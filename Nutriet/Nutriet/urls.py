"""URL configuration for Nutriet project."""

from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from pathlib import Path


def onesignal_sw_view(request):
    """
    Sirve el OneSignalSDKWorker.js desde la raíz del dominio.
    OneSignal exige que el SW esté en la raíz (/OneSignalSDKWorker.js).
    """
    sw_path = Path(__file__).resolve().parent.parent / 'OneSignalSDKWorker.js'
    try:
        content = sw_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        content = 'importScripts("https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.sw.js");'
    return HttpResponse(content, content_type='application/javascript')


urlpatterns = [
    path('admin/', admin.site.urls),

    # Usuarios (login, register, perfil, recuperar, verificación)
    path('usuarios/', include('applications.Usuarios.urls')),

    # Google OAuth
    path('api/auth/google/', include('applications.Usuarios.google_urls')),

    # Apps principales
    path('calendario/', include('applications.calendario.urls')),
    path('nutricion/',  include('applications.nutricion.urls')),
    path('seguimiento/', include('applications.seguimiento.urls')),
    path('notificaciones/', include('applications.notificacion.urls')),
    path('recetas/', include('applications.recetas.urls')),

    # Spoonacular (también sirve '/')
    path('', include('applications.Apispoonacular.urls')),

    # Home (al final porque captura '/')
    path('', include('applications.home.urls')),

    # Service Worker de OneSignal — DEBE estar en la raíz del dominio
    path('OneSignalSDKWorker.js', onesignal_sw_view, name='onesignal-sw'),
]
