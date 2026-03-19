from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.views.generic import FormView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
User = get_user_model()
from .forms import RegistroForm, LoginForm
from django.contrib import messages
import random
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from .forms import PerfilForm, CambiarPasswordForm
from django.views.decorators.cache import never_cache
from django.core.cache import cache

from .models import VerificacionCodigo
from django.utils import timezone
from datetime import timedelta, datetime
from applications.seguimiento.models import MedicionFisica
from applications.Apispoonacular.models import RecetaFavorita
import logging

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_ip(request):
    """IP real del cliente detrás del proxy de Render."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _rate_limited(key, max_requests, period_seconds):
    """True = bloqueado. False = permitido."""
    current = cache.get(key, 0)
    if current >= max_requests:
        return True
    cache.set(key, current + 1, timeout=period_seconds)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICACIÓN DE CÓDIGO (2FA login)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def verificacion_login(request):
    verificacion = VerificacionCodigo.objects.filter(usuario=request.user).first()

    if not verificacion:
        return redirect("/main/?setup_notifications=true")

    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip()

        if verificacion.esta_expirado():
            return render(request, "login/verificacion_login.html", {
                "error": "El código expiró. Inicia sesión nuevamente."
            })

        if codigo == verificacion.codigo:
            verificacion.verificado = True
            verificacion.save()
            return redirect("/main/?setup_notifications=true")
        else:
            return render(request, "login/verificacion_login.html", {
                "error": "Código incorrecto."
            })

    return render(request, "login/verificacion_login.html")


# ─────────────────────────────────────────────────────────────────────────────
# RECUPERACIÓN DE CONTRASEÑA
# ─────────────────────────────────────────────────────────────────────────────

def send_verification_code(request):
    """Solicita correo y envía código de recuperación."""
    if request.method == 'POST':
        ip    = _get_ip(request)
        email = request.POST.get('email', '').strip()

        if not email or '@' not in email:
            messages.error(request, 'Ingresa un correo válido.')
            return redirect('send_verification_code')

        # ✅ FIX: rate limit — máx 3 solicitudes por IP cada 15 minutos
        rl_key = f"recover_rl:{ip}"
        if _rate_limited(rl_key, max_requests=3, period_seconds=900):
            logger.warning(f"Rate limit recover — IP: {ip}")
            messages.error(request, 'Demasiados intentos. Espera 15 minutos.')
            return redirect('send_verification_code')

        # ✅ FIX CRÍTICO: respuesta SIEMPRE igual, no revelar si el email existe
        # Antes respondía "El correo no está registrado" → enumeración de usuarios
        if User.objects.filter(email=email).exists():
            code = str(random.randint(100000, 999999))
            request.session['verification_code'] = code
            request.session['email']              = email
            request.session['code_generated_at'] = timezone.now().isoformat()

            send_mail(
                'Código de recuperación — Nutriet',
                f'¡Hola!\nTu código de recuperación es: {code}\n'
                'Este código expira en 10 minutos.\n'
                'Si no solicitaste esto, ignora este correo.',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=True,
            )

        # Misma respuesta siempre, exista o no el email
        messages.success(request, 'Si el correo está registrado, recibirás un código en tu bandeja.')
        return redirect('verify_code')

    return render(request, 'recuperar/recuperar_contraseña.html')


def verify_code(request):
    """Valida el código de recuperación."""
    if request.method == 'POST':
        input_code     = request.POST.get('code', '').strip()
        session_code   = request.session.get('verification_code')
        email          = request.session.get('email')
        generated_at_s = request.session.get('code_generated_at')

        if not session_code or not email:
            messages.error(request, 'Sesión expirada. Solicita un nuevo código.')
            return redirect('send_verification_code')

        # ✅ FIX: verificar expiración de 10 minutos
        if generated_at_s:
            try:
                generated_at = datetime.fromisoformat(generated_at_s)
                if timezone.is_naive(generated_at):
                    generated_at = timezone.make_aware(generated_at)
                if timezone.now() > generated_at + timedelta(minutes=10):
                    for k in ('verification_code', 'email', 'code_generated_at'):
                        request.session.pop(k, None)
                    messages.error(request, 'El código expiró. Solicita uno nuevo.')
                    return redirect('send_verification_code')
            except (ValueError, TypeError):
                pass

        # ✅ FIX: rate limit en verificación — máx 5 intentos por IP
        ip     = _get_ip(request)
        rl_key = f"verify_rl:{ip}:{email}"
        if _rate_limited(rl_key, max_requests=5, period_seconds=600):
            messages.error(request, 'Demasiados intentos. Solicita un nuevo código.')
            for k in ('verification_code', 'email', 'code_generated_at'):
                request.session.pop(k, None)
            return redirect('send_verification_code')

        if input_code == session_code:
            return redirect('change_password')
        else:
            messages.error(request, 'Código incorrecto.')
            return redirect('verify_code')

    return render(request, 'recuperar/codigo_recuperacion.html')


@never_cache
def change_password(request):
    """Cambia la contraseña después de validar el código."""
    email        = request.session.get('email')
    session_code = request.session.get('verification_code')

    # ✅ FIX: sin sesión activa de recuperación, bloquear acceso directo a /cambiar/
    if not email or not session_code:
        messages.error(request, 'Primero solicita un código de recuperación.')
        return redirect('send_verification_code')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm  = request.POST.get('confirm_password', '')

        if password != confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('change_password')

        if len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return redirect('change_password')

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
        except User.DoesNotExist:
            messages.error(request, 'Error al actualizar la contraseña.')
            return redirect('send_verification_code')

        for k in ('email', 'verification_code', 'code_generated_at'):
            request.session.pop(k, None)

        messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
        return redirect('login')

    return render(request, 'recuperar/cambiar_contraseña.html')


@login_required
def reenviar_codigo(request):
    user         = request.user
    verificacion = VerificacionCodigo.objects.filter(usuario=user).first()

    if not verificacion:
        return redirect('main')

    if timezone.now() < verificacion.creado + timedelta(seconds=60):
        messages.error(request, "Debes esperar 60 segundos antes de reenviar el código.")
        return redirect('verificacion_login')

    verificacion.generar_codigo()

    send_mail(
        'Nuevo código de acceso — Nutriet',
        f'Tu nuevo código es: {verificacion.codigo}\n\nExpira en 5 minutos.',
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )

    messages.success(request, "Se envió un nuevo código a tu correo.")
    return redirect('verificacion_login')


class PasswordView(TemplateView):
    template_name = 'recuperar/recuperar_contraseña.html'


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────────────────────────────────────────

class RegisterView(FormView):
    template_name = 'login/register.html'
    form_class    = RegistroForm
    success_url   = reverse_lazy('nutricion:formulario')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        login(self.request, user)

        try:
            verificacion, _ = VerificacionCodigo.objects.get_or_create(usuario=user)
            verificacion.generar_codigo()

            send_mail(
                'Código de acceso — Nutriet',
                f'Hola!\n\nTu código de acceso es: {verificacion.codigo}\n\nEste código expira en 5 minutos.',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )

            messages.info(self.request, "Te enviamos un código de verificación a tu correo.")
            return redirect('verificacion_login')

        except Exception:
            messages.success(self.request, f"¡Registro exitoso! Bienvenido a Nutriet, {user.first_name or user.username}!")
            return redirect('/main/?setup_notifications=true')

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, error)
        return self.render_to_response(self.get_context_data(form=form))


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario          = form.save(commit=False)
            usuario.password = make_password(form.cleaned_data["password"])
            usuario.save()
            messages.success(request, "¡Registro exitoso! Ya puedes iniciar sesión.")
            return redirect('/main/?setup_notifications=true')
        else:
            messages.error(request, "Hay errores en el formulario. Revisa los campos.")
    else:
        form = RegistroForm()

    return render(request, "usuarios/registro.html", {"form": form})


CUSTOM_BACKEND = 'applications.Usuarios.backends.CustomAuthBackend'


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN  ✅ FIX: rate limit por IP — evita fuerza bruta
# ─────────────────────────────────────────────────────────────────────────────

class LoginView(FormView):
    form_class    = LoginForm
    template_name = 'login/login.html'

    def form_valid(self, form):
        ip                 = _get_ip(self.request)
        email_ingresado    = form.cleaned_data.get('email')
        password_ingresada = form.cleaned_data.get('password')

        # ✅ FIX CRÍTICO: máx 10 intentos por IP cada 15 minutos
        # Sin esto, un bot puede probar miles de contraseñas sin bloquearse
        rl_key = f"login_rl:{ip}"
        if _rate_limited(rl_key, max_requests=10, period_seconds=900):
            logger.warning(f"Rate limit login — IP: {ip} email: {email_ingresado}")
            messages.error(
                self.request,
                'Demasiados intentos fallidos. Espera 15 minutos e inténtalo de nuevo.'
            )
            return self.form_invalid(form)

        try:
            user = User.objects.get(email=email_ingresado)
        except User.DoesNotExist:
            user = None

        if user is not None and user.check_password(password_ingresada):
            # Login correcto — limpiar contador de intentos fallidos
            cache.delete(f"login_rl:{ip}")
            login(self.request, user)
            nombre = user.first_name if user.first_name else user.username

            try:
                verificacion, _ = VerificacionCodigo.objects.get_or_create(usuario=user)
                verificacion.generar_codigo()

                send_mail(
                    'Código de acceso — Nutriet',
                    f'Hola {nombre}!\n\nTu código de acceso es: {verificacion.codigo}\n\nEste código expira en 5 minutos.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )

                messages.info(
                    self.request,
                    f"¡Bienvenido a Nutriet, {nombre}! Te enviamos un código de verificación a tu correo."
                )
                return redirect('verificacion_login')

            except Exception:
                messages.success(self.request, f"¡Bienvenido a Nutriet, {nombre}!")
                return redirect('main')

        messages.error(self.request, 'Correo o contraseña incorrectos.')
        return self.form_invalid(form)


# ─────────────────────────────────────────────────────────────────────────────
# PERFIL
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@never_cache
def perfil_usuario(request):
    usuario    = request.user
    active_tab = 'perfil'

    perfil_form   = PerfilForm(instance=usuario)
    password_form = CambiarPasswordForm()

    if request.method == 'POST':

        if 'guardar_foto' in request.POST:
            perfil_form = PerfilForm(data=None, files=request.FILES, instance=usuario)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Foto de perfil actualizada correctamente.')
            else:
                messages.error(request, 'No se pudo actualizar la foto. Revisa el archivo e inténtalo de nuevo.')
            return redirect('perfil')

        elif 'guardar_datos' in request.POST:
            perfil_form = PerfilForm(request.POST, request.FILES, instance=usuario)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Datos actualizados correctamente.')
                return redirect('perfil')
            else:
                active_tab = 'perfil'
                messages.error(request, 'Revisa los campos e inténtalo de nuevo.')

        elif 'guardar_password' in request.POST:
            active_tab    = 'seguridad'
            password_form = CambiarPasswordForm(request.POST)

            password_old     = request.POST.get('password_old', '').strip()
            password_new     = request.POST.get('password_new', '').strip()
            password_confirm = request.POST.get('password_confirm', '').strip()

            if not usuario.check_password(password_old):
                messages.error(request, 'La contraseña actual es incorrecta.')
            elif password_new != password_confirm:
                messages.error(request, 'Las contraseñas nuevas no coinciden.')
            elif len(password_new) < 8:
                messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
            else:
                usuario.set_password(password_new)
                usuario.save()
                update_session_auth_hash(request, usuario)
                messages.success(request, '¡Contraseña actualizada correctamente!')
                return redirect('perfil')

        elif 'eliminar_cuenta' in request.POST:
            usuario.delete()
            messages.success(request, 'Tu cuenta ha sido eliminada.')
            return redirect('login')

    favoritas        = RecetaFavorita.objects.filter(usuario=usuario)
    dias_registrados = MedicionFisica.objects.filter(usuario=usuario).count()
    progreso         = min(int((dias_registrados / 30) * 100), 100)

    return render(request, 'configuracion/perfil.html', {
        'perfil_form':      perfil_form,
        'password_form':    password_form,
        'usuario':          usuario,
        'active_tab':       active_tab,
        'favoritas':        favoritas,
        'dias_registrados': dias_registrados,
        'progreso':         progreso,
    })


@login_required
def marcar_notificaciones_configuradas(request):
    from django.http import JsonResponse
    request.user.notificaciones_configuradas = True
    request.user.save(update_fields=['notificaciones_configuradas'])
    return JsonResponse({'ok': True})