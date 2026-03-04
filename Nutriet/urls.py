"""
URL configuration for Nutriet project.
"""
from django.contrib import admin
from django.urls import path, include
from applications.Usuarios.views import RegisterView, LoginView, PasswordView
from applications.home.views import MainViews
from django.http import HttpResponse
from pathlib import Path


def firebase_sw_view(request):
    """
    Sirve el firebase-messaging-sw.js directamente desde el filesystem.
    Evita el error TemplateDoesNotExist porque NO usa el sistema de templates de Django.
    """
    sw_path = Path(__file__).resolve().parent.parent / 'firebase-messaging-sw.js'
    try:
        content = sw_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return HttpResponse('// Service Worker not found', content_type='application/javascript', status=404)
    return HttpResponse(content, content_type='application/javascript')


urlpatterns = [
    path('admin/', admin.site.urls),
    # Rutas específicas primero (antes de include vacío de home)
    path('usuarios/', include('applications.Usuarios.urls')),
    path('calendario/', include('applications.calendario.urls')),
    path('nutricion/', include('applications.nutricion.urls')),
    path('', include('applications.Apispoonacular.urls')),
    path("seguimiento/", include("applications.seguimiento.urls")),


    # Include vacío de home DEBE IR AL FINAL
    path('', include('applications.home.urls')),
    path('api/auth/google/', include('applications.Usuarios.google_urls')),

    path('notificaciones/', include('applications.notificacion.urls')),

    # Recetas MealDB
    path('recetas/', include('applications.recetas.urls')),

    # Service Worker para Firebase — se sirve directamente como archivo estático
    path('firebase-messaging-sw.js', firebase_sw_view, name='firebase-sw'),

]

# ── Health Check (para uptime monitors y PaaS) ────────────────────────────────
from applications.home.views import health_check as health_check_view
urlpatterns += [
    path('health/', health_check_view, name='health_check'),
]
