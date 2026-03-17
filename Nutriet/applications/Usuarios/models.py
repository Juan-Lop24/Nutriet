from django.contrib.auth.models import AbstractUser
from django.db import models
#CODIGO PARA ENTRAR EL APLICATIVO
import random
from django.utils import timezone
from datetime import timedelta



class Usuario(AbstractUser):
    """
    Custom user model used by the project.
    Se agregan los campos requeridos por las forms y modelos del proyecto:
    - nombre: para mantener compatibilidad con los templates/str del proyecto
    - telefono: utilizado por el formulario de registro
    """
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='perfil/', blank=True, null=True)
    notificaciones_configuradas = models.BooleanField(default=False)

    def __str__(self):
        # Mantener un nombre legible; si no hay nombre, usar el username
        return self.username
    
class VerificacionCodigo(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    creado = models.DateTimeField(auto_now=True)
    verificado = models.BooleanField(default=False)

    def generar_codigo(self):
        self.codigo = str(random.randint(100000, 999999))
        self.verificado = False
        self.creado = timezone.now()
        self.save()

    def esta_expirado(self):
        return timezone.now() > self.creado + timedelta(minutes=5)
    