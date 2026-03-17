# applications/notificacion/serializers.py
"""
Serializers para las APIs de notificaciones
"""

from rest_framework import serializers
from .models import DispositivoUsuario, Notificacion


class DispositivoUsuarioSerializer(serializers.ModelSerializer):
    """Serializer para el modelo DispositivoUsuario"""
    
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    
    class Meta:
        model = DispositivoUsuario
        fields = [
            'id',
            'usuario',
            'usuario_username',
            'token_fcm',
            'nombre_dispositivo',
            'sistema_operativo',
            'activo',
            'fecha_registro',
            'ultima_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_registro', 'ultima_actualizacion', 'usuario']


class NotificacionSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Notificacion"""
    
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    
    class Meta:
        model = Notificacion
        fields = [
            'id',
            'usuario',
            'usuario_username',
            'titulo',
            'cuerpo',
            'imagen_url',
            'datos_adicionales',
            'estado',
            'respuesta_firebase',
            'fecha_envio'
        ]
        read_only_fields = ['id', 'fecha_envio', 'usuario']