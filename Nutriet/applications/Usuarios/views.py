from django.shortcuts import render,redirect
from django.contrib.auth import login
from django.views.generic import FormView,TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
User = get_user_model()
from .forms import RegistroForm,LoginForm
from django.contrib import messages
import random
from django.core.mail import send_mail
from django.conf import settings
#OTRO NUEVO
from django.contrib.auth.hashers import make_password
#MAS CLASES
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from .forms import PerfilForm, CambiarPasswordForm
from django.views.decorators.cache import never_cache

#verificacion de codigo
from .models import VerificacionCodigo
from django.utils import timezone
from datetime import timedelta
from applications.seguimiento.models import MedicionFisica
from applications.Apispoonacular.models import RecetaFavorita


@login_required
def verificacion_login(request):
    

    verificacion = VerificacionCodigo.objects.filter(usuario=request.user).first()

    if not verificacion:
        return redirect("/main/?setup_notifications=true")

    if request.method == "POST":
        codigo = request.POST.get("codigo")

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
                "error": "Código incorrecto"
            })

    return render(request, "login/verificacion_login.html")

#HASTA ACA TERMINA LA LOGICA DE VERIFICACION DE CODIGO PARA INICIAR SESION


def send_verification_code(request):
    """Vista para solicitar el correo y enviar el código de recuperación"""
    if request.method == 'POST':
        email = request.POST.get('email')

        # Verificar si el correo existe
        if not User.objects.filter(email=email).exists():
            messages.error(request, 'El correo no está registrado.')
            return redirect('send_verification_code')

        # Generar código de 6 dígitos
        code = str(random.randint(100000, 999999))

        # Guardar código y correo en la sesión
        request.session['verification_code'] = code
        request.session['email'] = email

        # Enviar el correo con el código
        send_mail(
            'Código de recuperación',
            f'¡Hola!\nTu código de recuperacion de contraseña es: {code}\n'
            'Este código expira en unos minutos, así que te aconsejamos usarlo pronto\n'
            'Gracias por confiar en nosotros 💛',
            settings.EMAIL_HOST_USER,  # Desde el correo configurado
            [email],             # Destinatario
            fail_silently=False,
        )

        messages.success(request, 'Se esta enviando un código a tu correo electronico.')
        return redirect('verify_code')  # Página para ingresar el código

    return render(request, 'recuperar/recuperar_contraseña.html')


def verify_code(request):
    """Vista para ingresar y validar el código de recuperación"""
    if request.method == 'POST':
        input_code = request.POST.get('code')
        session_code = request.session.get('verification_code')
        email = request.session.get('email')

        if input_code == session_code:
            # Código correcto → redirigir a cambio de contraseña
            return redirect('change_password')
        else:
            messages.error(request, 'Código incorrecto.')
            return redirect('verify_code')

    return render(request, 'recuperar/codigo_recuperacion.html')


def change_password(request):
    """Vista para cambiar la contraseña después de validar el código"""
    email = request.session.get('email')

    if not email:
        messages.error(request, 'Primero solicita un código de recuperación.')
        return redirect('send_verification_code')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('change_password')

        # Cambiar contraseña del usuario
        user = User.objects.get(email=email)
        user.set_password(password)
        user.save()

        # Limpiar sesión
        del request.session['email']
        del request.session['verification_code']

        messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
        return redirect('login')

    return render(request, 'recuperar/cambiar_contraseña.html')

@login_required
def reenviar_codigo(request):
    user = request.user

    verificacion = VerificacionCodigo.objects.filter(usuario=user).first()

    if not verificacion:
        return redirect('/main/?setup_notifications=true')

    # 🔒 Anti spam 60 segundos
    if timezone.now() < verificacion.creado + timedelta(seconds=60):
        messages.error(request, "Debes esperar 60 segundos antes de reenviar el código.")
        return redirect('verificacion_login')

    # 🔄 Generar nuevo código
    verificacion.generar_codigo()

    # 📧 Enviar correo
    send_mail(
        'Nuevo código de acceso - NUTRIET',
        f'Tu nuevo código es: {verificacion.codigo}\n\nExpira en 5 minutos.',
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )

    messages.success(request, "Se envió un nuevo código a tu correo.")
    return redirect('verificacion_login')


class PasswordView(TemplateView):
    template_name = 'recuperar/recuperar_contraseña.html'
    def home(request):
        return render(request, "recuperar_contraseña.html")



class RegisterView(FormView):
    template_name = 'login/register.html'
    form_class = RegistroForm
    success_url = reverse_lazy('nutricion:formulario')

    def form_valid(self, form):
        # ── 1. Crear el usuario ──────────────────────────────────────
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()

        # ── 2. Iniciar sesión automáticamente ────────────────────────
        login(self.request, user)

        # ── 3. Generar y enviar código de verificación ───────────────
        try:
            verificacion, _ = VerificacionCodigo.objects.get_or_create(usuario=user)
            verificacion.generar_codigo()

            send_mail(
                'Código de acceso - NUTRIET',
                f'Hola 👋\n\nTu código de acceso es: {verificacion.codigo}\n\nEste código expira en 5 minutos.',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )

            messages.info(self.request, "Te enviamos un código de verificación a tu correo.")
            # Si el correo se envió → ir a verificación
            return redirect('verificacion_login')

        except Exception:
            # Si el correo falla → saltar verificación, ir directo con notificaciones
            messages.success(self.request, f"¡Registro exitoso! Bienvenido a Nutriet, {user.first_name or user.username} 👋")
            return redirect('/main/?setup_notifications=true')

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, error)
        return self.render_to_response(self.get_context_data(form=form))


# ── REGISTRO FUNCIONAL (vista alternativa) ───────────────────────────────────
def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)

        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.password = make_password(form.cleaned_data["password"])
            usuario.save()

            messages.success(request, "¡Registro exitoso! Ya puedes iniciar sesión.")
            return redirect('/main/?setup_notifications=true')
        else:
            messages.error(request, "Hay errores en el formulario. Revisa los campos.")
    else:
        form = RegistroForm()

    return render(request, "usuarios/registro.html", {"form": form})

# Define la ruta de tu backend personalizado (Asegúrate de que esta sea la correcta)
CUSTOM_BACKEND = 'applications.Usuarios.backends.CustomAuthBackend'

class LoginView(FormView):
    form_class = LoginForm
    template_name = 'login/login.html'

    def form_valid(self, form):
        email_ingresado = form.cleaned_data.get('email')
        password_ingresada = form.cleaned_data.get('password')

        try:
            user = User.objects.get(email=email_ingresado)
        except User.DoesNotExist:
            user = None

        if user is not None and user.check_password(password_ingresada):
            login(self.request, user)

            nombre = user.first_name if user.first_name else user.username

            # ── Generar y enviar código de verificación ──────────────
            try:
                verificacion, _ = VerificacionCodigo.objects.get_or_create(usuario=user)
                verificacion.generar_codigo()

                send_mail(
                    'Código de acceso - NUTRIET',
                    f'Hola {nombre} 👋\n\nTu código de acceso es: {verificacion.codigo}\n\nEste código expira en 5 minutos.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )

                messages.info(
                    self.request,
                    f"¡Bienvenido a Nutriet, {nombre}! 👋 Te enviamos un código de verificación a tu correo."
                )
                return redirect('verificacion_login')

            except Exception:
                # Si el correo falla → entrar sin verificación
                messages.success(self.request, f"¡Bienvenido a Nutriet, {nombre}! 👋")
                return redirect('/main/?setup_notifications=true')

        messages.error(self.request, 'Correo o contraseña incorrectos.')
        return self.form_invalid(form)
        

# ─────────────────────────────────────────────────────
# PERFIL DE USUARIO
# ─────────────────────────────────────────────────────

@login_required
@never_cache
def perfil_usuario(request):
    usuario    = request.user
    active_tab = 'perfil'          # tab abierto por defecto

    # Forms vacíos para GET
    perfil_form   = PerfilForm(instance=usuario)
    password_form = CambiarPasswordForm()

    if request.method == 'POST':

        # ── 1. GUARDAR FOTO ───────────────────────────────────────────
        if 'guardar_foto' in request.POST:
            # Solo archivos; no validamos campos de texto para evitar errores
            perfil_form = PerfilForm(data=None, files=request.FILES, instance=usuario)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Foto de perfil actualizada correctamente.')
            else:
                messages.error(request, 'No se pudo actualizar la foto. Revisa el archivo e inténtalo de nuevo.')
            return redirect('perfil')

        # ── 2. GUARDAR DATOS PERSONALES ───────────────────────────────
        elif 'guardar_datos' in request.POST:
            perfil_form = PerfilForm(request.POST, request.FILES, instance=usuario)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Datos actualizados correctamente.')
                return redirect('perfil')
            else:
                active_tab = 'perfil'
                messages.error(request, 'Revisa los campos e inténtalo de nuevo.')

        # ── 3. CAMBIAR CONTRASEÑA ─────────────────────────────────────
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
                # Mantiene la sesión activa sin re-login
                update_session_auth_hash(request, usuario)
                messages.success(request, '¡Contraseña actualizada correctamente!')
                return redirect('perfil')

        # ── 4. ELIMINAR CUENTA ────────────────────────────────────────
        elif 'eliminar_cuenta' in request.POST:
            usuario.delete()
            messages.success(request, 'Tu cuenta ha sido eliminada.')
            return redirect('login')

    # ── DATOS DE CONTEXTO ─────────────────────────────────────────────
    favoritas        = RecetaFavorita.objects.filter(usuario=usuario)
    dias_registrados = MedicionFisica.objects.filter(usuario=usuario).count()

    # Progreso: número de mediciones sobre 30 días objetivo (máx 100%)
    progreso = min(int((dias_registrados / 30) * 100), 100)

    return render(request, 'configuracion/perfil.html', {
        'perfil_form':    perfil_form,
        'password_form':  password_form,
        'usuario':        usuario,
        'active_tab':     active_tab,     # abre el tab correcto tras POST con error
        'favoritas':      favoritas,
        'dias_registrados': dias_registrados,
        'progreso':       progreso,
    })

@login_required
def marcar_notificaciones_configuradas(request):
    """Marca que el usuario ya vio/configuró el prompt de notificaciones."""
    from django.http import JsonResponse
    request.user.notificaciones_configuradas = True
    request.user.save(update_fields=['notificaciones_configuradas'])
    return JsonResponse({'ok': True})