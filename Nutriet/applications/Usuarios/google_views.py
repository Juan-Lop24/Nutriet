import re
import requests
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import get_user_model, login

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
        return redirect("login")

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
        return redirect("login")

    # ========= 2. Obtener datos del usuario =========
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    info = requests.get(userinfo_url, headers=headers).json()

    email = info.get("email")
    name = info.get("name", "")

    if not email:
        return redirect("login")

    # ========= 3. Generar username único =========
    base_username = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0]) or "user"
    username = base_username
    i = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}{i}"
        i += 1

    # ========= 4. Buscar o crear usuario =========
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": username,
            "first_name": name,
        }
    )

    if created:
        user.set_unusable_password()
        user.save()

    # ========= 5. Iniciar sesión =========
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # ========= 6. Si es nuevo usuario → enviar verificación =========
    if created:
        from .models import VerificacionCodigo
        from django.core.mail import send_mail

        verificacion, _ = VerificacionCodigo.objects.get_or_create(usuario=user)
        verificacion.generar_codigo()

        send_mail(
            'Código de verificación - Nutriet',
            f'Tu código de verificación es: {verificacion.codigo}\n\nEste código expira en 5 minutos.',
            'noreply@nutriet.com',
            [user.email],
            fail_silently=False,
        )

        return redirect("/usuarios/verificacion-login/")

    # ========= 7. Usuario existente =========
    else:
        if getattr(user, "notificaciones_configuradas", False):
            return redirect("/main/")
        else:
            return redirect("/main/?setup_notifications=true")