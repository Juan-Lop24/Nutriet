# En tu archivo backends.py

from django.contrib.auth import get_user_model
Usuario = get_user_model()
from django.contrib.auth.hashers import check_password

class CustomAuthBackend:
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        # NOTA: Usamos 'email' aquí para coincidir con tu USERNAME_FIELD
        try:
            # 1. Buscar el usuario por email
            user = Usuario.objects.get(email=email)
            # 2. Verificar la contraseña
            if user.is_active and check_password(password, user.password):
                return user
        except Usuario.DoesNotExist:
            # Si el correo no existe en la base de datos
            return None
        return None

    def get_user(self, user_id):
        # Esta función es requerida para el manejo de sesiones
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None