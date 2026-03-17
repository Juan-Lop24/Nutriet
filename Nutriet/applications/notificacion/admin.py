# applications/notificacion/admin.py
"""
Configuración del admin de Django para notificaciones
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import DispositivoUsuario, Notificacion


@admin.register(DispositivoUsuario)
class DispositivoUsuarioAdmin(admin.ModelAdmin):
    """Admin para gestionar dispositivos de usuarios"""

    list_display = [
        'estado_icon',
        'usuario',
        'nombre_dispositivo_display',
        'sistema_operativo',
        'token_preview',
        'fecha_registro',
        'ultima_actualizacion'
    ]

    list_filter = [
        'activo',
        'sistema_operativo',
        'fecha_registro'
    ]

    search_fields = [
        'usuario__username',
        'usuario__email',
        'token_fcm',
        'nombre_dispositivo'
    ]

    readonly_fields = [
        'fecha_registro',
        'ultima_actualizacion',
        'token_completo'
    ]

    fieldsets = (
        ('Información del Usuario', {
            'fields': ('usuario', 'nombre_dispositivo', 'sistema_operativo')
        }),
        ('Token FCM', {
            'fields': ('token_fcm', 'token_completo', 'activo')
        }),
        ('Fechas', {
            'fields': ('fecha_registro', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    actions = ['marcar_activos', 'marcar_inactivos']

    def estado_icon(self, obj):
        """Muestra un ícono visual del estado"""
        if obj.activo:
            return format_html(
                '<span style="color: green; font-size: 16px;">●</span> {}',
                'Activo'
            )
        return format_html(
            '<span style="color: red; font-size: 16px;">●</span> {}',
            'Inactivo'
        )
    estado_icon.short_description = 'Estado'

    def nombre_dispositivo_display(self, obj):
        """Muestra el nombre del dispositivo o un valor por defecto"""
        return obj.nombre_dispositivo or 'Dispositivo Web'
    nombre_dispositivo_display.short_description = 'Dispositivo'

    def token_preview(self, obj):
        """Muestra una preview del token (primeros y últimos caracteres)"""
        if obj.token_fcm and len(obj.token_fcm) > 20:
            return f"{obj.token_fcm[:10]}...{obj.token_fcm[-10:]}"
        return obj.token_fcm or "-"
    token_preview.short_description = 'Token (preview)'

    def token_completo(self, obj):
        """Muestra el token completo en el formulario de detalle"""
        return format_html(
            '<textarea readonly style="width: 100%; height: 100px; font-family: monospace;">{}</textarea>',
            obj.token_fcm or ""
        )
    token_completo.short_description = 'Token Completo'

    def marcar_activos(self, request, queryset):
        """Acción para marcar dispositivos seleccionados como activos"""
        updated = queryset.update(activo=True)
        self.message_user(request, f'{updated} dispositivo(s) marcado(s) como activo(s)')
    marcar_activos.short_description = "Marcar como activos"

    def marcar_inactivos(self, request, queryset):
        """Acción para marcar dispositivos seleccionados como inactivos"""
        updated = queryset.update(activo=False)
        self.message_user(request, f'{updated} dispositivo(s) marcado(s) como inactivo(s)')
    marcar_inactivos.short_description = "Marcar como inactivos"


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    """Admin para ver el historial de notificaciones"""

    list_display = [
        'estado_badge',
        'titulo',
        'usuario',
        'fecha_envio_display',
        'tiene_imagen'
    ]

    list_filter = [
        'estado',
        'fecha_envio'
    ]

    search_fields = [
        'usuario__username',
        'usuario__email',
        'titulo',
        'cuerpo'
    ]

    readonly_fields = [
        'usuario',
        'titulo',
        'cuerpo',
        'imagen_url',
        'datos_adicionales',
        'estado',
        'respuesta_firebase',
        'fecha_envio'
    ]

    fieldsets = (
        ('Destinatario', {
            'fields': ('usuario',)
        }),
        ('Contenido', {
            'fields': ('titulo', 'cuerpo', 'imagen_url')
        }),
        ('Datos Técnicos', {
            'fields': ('datos_adicionales', 'estado', 'respuesta_firebase', 'fecha_envio'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """No permitir crear notificaciones desde el admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """No permitir editar notificaciones"""
        return False

    def estado_badge(self, obj):
        """Muestra el estado con un badge de color"""
        colors = {
            'enviada': '#17a2b8',   # azul
            'entregada': '#28a745', # verde
            'error': '#dc3545'      # rojo
        }
        color = colors.get(obj.estado, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_estado_display().upper()
        )
    estado_badge.short_description = 'Estado'

    def fecha_envio_display(self, obj):
        """Formatea la fecha de envío"""
        if obj.fecha_envio:
            return obj.fecha_envio.strftime('%d/%m/%Y %H:%M')
        return "-"
    fecha_envio_display.short_description = 'Fecha de Envío'

    def tiene_imagen(self, obj):
        """Indica si la notificación tiene imagen"""
        if obj.imagen_url:
            return format_html('<span style="color: green;">{}</span>', '✓')
        return format_html('<span style="color: #ccc;">{}</span>', '—')
    tiene_imagen.short_description = 'Imagen'
