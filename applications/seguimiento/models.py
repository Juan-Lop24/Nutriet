from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from applications.nutricion.models import FormularioNutricionGuardado


FRECUENCIA_CHOICES = [
    (1,  'Cada 24 horas'),
    (15, 'Cada 15 días'),
    (30, 'Cada mes'),
]


class PreferenciaMedicion(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferencia_medicion'
    )
    frecuencia_dias = models.PositiveIntegerField(
        choices=FRECUENCIA_CHOICES,
        default=15,
        verbose_name='Frecuencia de medición (días)'
    )
    configurada = models.BooleanField(
        default=False,
        verbose_name='El usuario ya eligió su frecuencia'
    )

    class Meta:
        verbose_name = 'Preferencia de Medición'
        verbose_name_plural = 'Preferencias de Medición'

    def __str__(self):
        return f"{self.usuario} — cada {self.frecuencia_dias} días"



class MedicionFisica(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    fecha = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    peso = models.FloatField(verbose_name="Peso (kg)")
    altura = models.FloatField(verbose_name="Altura (cm)")

    imc = models.FloatField(null=True, blank=True)
    grasa_corporal = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['fecha']
        verbose_name = "Medición Física"
        verbose_name_plural = "Mediciones Físicas"

def clean(self):
    if not self.usuario_id:
        return

    formulario = FormularioNutricionGuardado.objects.filter(
        usuario=self.usuario
    ).last()

    if not formulario:
        return

    #  No permitir peso mayor a la meta
    if self.peso > formulario.peso_objetivo:
        raise ValidationError({
            "peso": f"No puedes registrar un peso mayor a tu meta establecida ({formulario.peso_objetivo} kg)."
        })

    #  No permitir peso menor a 40 kg
    if self.peso < 40:
        raise ValidationError({
            "peso": "El peso no puede ser menor a 40 kg."
        })

    def __str__(self):
        return f"{self.usuario} — {self.fecha} | {self.peso} kg"

