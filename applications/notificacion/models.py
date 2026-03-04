# applications/notificacion/models.py
"""
Modelos para el sistema de notificaciones push con Firebase Cloud Messaging (FCM)

Características:
- Permite múltiples usuarios en el mismo dispositivo/navegador
- Actualiza tokens existentes sin crear duplicados
- Mantiene tokens activos incluso cuando el usuario cierra sesión
- Marca tokens como inactivos solo cuando Firebase reporta errores
"""

from django.db import models
from django.conf import settings


class DispositivoUsuario(models.Model):
    """
    Modelo para almacenar tokens FCM de dispositivos
    
    Un token FCM identifica un navegador/dispositivo específico.
    Múltiples usuarios pueden tener tokens del mismo dispositivo.
    """
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dispositivos',
        help_text='Usuario dueño de este token'
    )
    
    # Sin unique=True para permitir el mismo token en diferentes usuarios
    token_fcm = models.CharField(
        max_length=500,
        help_text='Token de Firebase Cloud Messaging'
    )
    
    nombre_dispositivo = models.CharField(
        max_length=100,
        blank=True,
        help_text='Ejemplo: Chrome - Windows, Firefox - MacOS'
    )
    
    sistema_operativo = models.CharField(
        max_length=20,
        choices=[
            ('Android', 'Android'),
            ('iOS', 'iOS'),
            ('Web', 'Web')
        ],
        default='Web'
    )
    
    activo = models.BooleanField(
        default=True,
        help_text='False si el token es reportado como inválido por Firebase'
    )
    
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text='Primera vez que se registró este token'
    )
    
    ultima_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text='Última vez que se usó este token'
    )

    class Meta:
        verbose_name = "Dispositivo Usuario"
        verbose_name_plural = "Dispositivos Usuarios"
        
        # La combinación usuario + token debe ser única
        # Esto permite: mismo token para diferentes usuarios ✅
        # Pero evita: mismo usuario con el mismo token duplicado ❌
        unique_together = ('usuario', 'token_fcm')
        
        # Índices para mejorar consultas
        indexes = [
            models.Index(fields=['usuario', 'activo'], name='notif_user_active_idx'),
            models.Index(fields=['token_fcm'], name='notif_token_idx'),
            models.Index(fields=['activo', 'ultima_actualizacion'], name='notif_active_updated_idx'),
        ]
        
        ordering = ['-ultima_actualizacion']

    def __str__(self):
        dispositivo = self.nombre_dispositivo or f'Dispositivo {self.sistema_operativo}'
        estado = '✓' if self.activo else '✗'
        return f"{estado} {self.usuario.username} - {dispositivo}"

    def marcar_como_inactivo(self):
        """Marca el dispositivo como inactivo (token inválido)"""
        self.activo = False
        self.save(update_fields=['activo', 'ultima_actualizacion'])


class Notificacion(models.Model):
    """
    Modelo para registrar historial de notificaciones enviadas
    Útil para auditoría y análisis
    """
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones_recibidas'
    )
    
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField()
    imagen_url = models.URLField(blank=True, null=True)
    
    datos_adicionales = models.JSONField(
        default=dict,
        blank=True,
        help_text='Datos extra enviados con la notificación (URLs, IDs, etc.)'
    )
    
    estado = models.CharField(
        max_length=20,
        choices=[
            ('enviada', 'Enviada'),
            ('entregada', 'Entregada'),
            ('error', 'Error')
        ],
        default='enviada'
    )
    
    respuesta_firebase = models.CharField(
        max_length=500,
        blank=True,
        help_text='ID de mensaje de Firebase o mensaje de error'
    )
    
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha_envio']
        
        indexes = [
            models.Index(fields=['usuario', '-fecha_envio'], name='notif_user_date_idx'),
            models.Index(fields=['estado'], name='notif_estado_idx'),
            models.Index(fields=['-fecha_envio'], name='notif_date_idx'),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username} ({self.get_estado_display()})"