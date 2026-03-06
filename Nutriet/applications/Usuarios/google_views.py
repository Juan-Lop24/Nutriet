import re
import requests
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.mail import send_mail

User = get_user_model()


def google_login(request):
    base = "https://accounts.google.com/o/oauth2/v2/auth"

    url = (
        f"{base}?response_type=code"
        f"&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&scope=openid email profile"
        f"&prompt=select_account"
    )
    return redirect(url)


def google_callback(request):
    code = request.GET.get("code")
    if not code:
        return redirect("/login/")

    # ========= 1. Obtener token =========
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    token_res = requests.post(token_url, data=data).json()
    access_token = token_res.get("access_token")

    if not access_token:
        return redirect("/login/")

    # ========= 2. Obtener datos del usuario =========
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    info = requests.get(userinfo_url, headers=headers).json()

    email = info.get("email")
    name = info.get("name", "")

    if not email:
        return redirect("/login/")

    # ========= 3. Buscar usuario =========
    from .models import VerificacionCodigo

    user = User.objects.filter(email=email).first()

    # ========= 4. BLOQUEO: usuario existe pero NO ha verificado su correo =========
    # Caso: se registró con email/contraseña, no verificó, e intenta entrar con Google
    if user is not None:
        verificacion = VerificacionCodigo.objects.filter(usuario=user).first()

        if verificacion and not verificacion.verificado:
            # Iniciar sesión temporalmente para que @login_required no lo bloquee
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Reenviar código de verificación
            verificacion.generar_codigo()
            try:
                send_mail(
                    'Código de verificación pendiente - Nutriet',
                    f'Hola 👋\n\nDetectamos que aún no has verificado tu correo.\n\nTu código es: {verificacion.codigo}\n\nEste código expira en 5 minutos.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                pass

            # Redirigir a verificación — no puede continuar sin verificar
            return redirect("/usuarios/verificacion-login/")

    # ========= 5. Crear usuario si no existe =========
    if not user:
        base_username = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0]) or "user"
        username = base_username
        i = 1

        while User.objects.filter(username=username).exists():
            username = f"{base_username}{i}"
            i += 1

        user = User.objects.create(
            username=username,
            email=email,
            first_name=name,
        )
        user.set_unusable_password()
        user.save()

    # ========= 6. Iniciar sesión =========
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # ========= 7. Verificación: solo si es la primera vez con Google =========
    verificacion, created = VerificacionCodigo.objects.get_or_create(usuario=user)

    # Si el usuario ya verificó su cuenta antes, lo dejamos pasar directo
    if verificacion.verificado:
        return redirect("/main/")

    # Primera vez con Google: generar y enviar código
    verificacion.generar_codigo()

    try:
        send_mail(
            'Código de verificación - Nutriet',
            f'Tu código de verificación es: {verificacion.codigo}\n\nEste código expira en 5 minutos.',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        pass

    return redirect("/usuarios/verificacion-login/")
