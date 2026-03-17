# applications/notificacion/urls.py
"""
URLs para las APIs de notificaciones push
"""

from django.urls import path
from . import views

app_name = 'notificacion'

urlpatterns = [
    # APIs para gestión de tokens FCM
    path('api/guardar-token-fcm/', views.guardar_token_fcm, name='guardar_token_fcm'),
    path('api/eliminar-token-fcm/', views.eliminar_token_fcm, name='eliminar_token_fcm'),
    path('api/dispositivos/', views.listar_dispositivos, name='listar_dispositivos'),
    path('api/marcar-inactivo/', views.marcar_dispositivo_inactivo, name='marcar_inactivo'),

    # NUEVAS: envío manual y gestión
    path('api/enviar-manual/', views.enviar_notificacion_manual, name='enviar_manual'),
    path('api/scheduler/', views.estado_scheduler, name='estado_scheduler'),
    path('api/diagnostico/', views.diagnostico_token, name='diagnostico'),

    # Panel de administración
    path('panel/', views.panel_notificaciones, name='panel_admin'),
]