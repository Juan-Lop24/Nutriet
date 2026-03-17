from django.db import models
from django.conf import settings


class Actividad(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='actividades_calendario',
        help_text='Usuario dueño de esta actividad'
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField()
    hora = models.TimeField(blank=True, null=True)
    notificacion_enviada = models.BooleanField(
        default=False,
        help_text='True cuando ya se envió la notificación previa de este evento'
    )

    class Meta:
        indexes = [
            models.Index(fields=['usuario', 'fecha'], name='cal_usuario_fecha_idx'),
            models.Index(fields=['fecha', 'hora'], name='cal_fecha_hora_idx'),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.fecha})"