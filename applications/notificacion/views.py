# applications/notificacion/views.py
"""
Vistas para el sistema de notificaciones push

APIs:
- guardar_token_fcm: Guarda o actualiza el token FCM del usuario
- eliminar_token_fcm: Elimina un token específico
- listar_dispositivos: Lista todos los dispositivos del usuario
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import DispositivoUsuario
from .serializers import DispositivoUsuarioSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def guardar_token_fcm(request):
    """
    Guarda o actualiza el token FCM del usuario
    
    Comportamiento:
    - Si el usuario YA tiene este token → Actualiza la fecha (no crea duplicado)
    - Si el usuario NO tiene este token → Crea un nuevo registro
    - Si el token estaba inactivo → Lo reactiva
    
    POST /notificaciones/api/guardar-token-fcm/
    Body: {
        "token": "token_fcm_aqui",
        "nombre_dispositivo": "Chrome - Windows",  // Opcional
        "sistema_operativo": "Web"  // Opcional: Web, Android, iOS
    }
    
    Response: {
        "success": true,
        "created": false,  // true si es nuevo, false si se actualizó
        "message": "Token actualizado exitosamente",
        "dispositivo": {...}
    }
    """
    try:
        token = request.data.get('token')
        nombre_dispositivo = request.data.get('nombre_dispositivo', 'Dispositivo Web')
        sistema_operativo = request.data.get('sistema_operativo', 'Web')

        if not token:
            return Response(
                {'error': 'El token es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Marcar como inactivos los tokens anteriores del mismo usuario/SO
        # que NO sean el token que se está registrando ahora.
        # Esto resuelve el problema de tokens zombies cuando el servidor reinicia
        # (especialmente en localhost) y Firebase genera un token nuevo.
        tokens_viejos_desactivados = DispositivoUsuario.objects.filter(
            usuario=request.user,
            sistema_operativo=sistema_operativo,
            activo=True,
        ).exclude(token_fcm=token).update(activo=False)

        # Guardar o actualizar el token actual
        dispositivo, created = DispositivoUsuario.objects.update_or_create(
            usuario=request.user,
            token_fcm=token,
            defaults={
                'nombre_dispositivo': nombre_dispositivo,
                'sistema_operativo': sistema_operativo,
                'activo': True
            }
        )

        serializer = DispositivoUsuarioSerializer(dispositivo)
        mensaje = 'Token guardado exitosamente' if created else 'Token actualizado exitosamente'

        return Response({
            'success': True,
            'created': created,
            'message': mensaje,
            'tokens_viejos_desactivados': tokens_viejos_desactivados,
            'dispositivo': serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Error al guardar el token: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_token_fcm(request):
    """
    Elimina un token FCM específico del usuario
    
    Útil cuando:
    - El usuario desactiva notificaciones manualmente
    - El usuario quiere desregistrar un dispositivo específico
    
    DELETE /notificaciones/api/eliminar-token-fcm/
    Body: {
        "token": "token_fcm_aqui"
    }
    
    Response: {
        "success": true,
        "message": "1 dispositivo(s) eliminado(s)"
    }
    """
    try:
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'error': 'El token es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar y eliminar solo el dispositivo de este usuario con este token
        dispositivos = DispositivoUsuario.objects.filter(
            usuario=request.user,
            token_fcm=token
        )
        
        if dispositivos.exists():
            count = dispositivos.count()
            dispositivos.delete()
            return Response({
                'success': True,
                'message': f'{count} dispositivo(s) eliminado(s)'
            })
        else:
            return Response({
                'success': False,
                'message': 'No se encontró el dispositivo'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response(
            {'error': f'Error al eliminar el token: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_dispositivos(request):
    """
    Lista todos los dispositivos del usuario
    
    GET /notificaciones/api/dispositivos/
    
    Query params opcionales:
    - activo=true/false: Filtrar por dispositivos activos o inactivos
    
    Response: {
        "success": true,
        "count": 2,
        "dispositivos": [...]
    }
    """
    try:
        # Filtro base: dispositivos del usuario actual
        dispositivos = DispositivoUsuario.objects.filter(usuario=request.user)
        
        # Filtro opcional por estado activo
        activo = request.query_params.get('activo')
        if activo is not None:
            activo_bool = activo.lower() in ('true', '1', 'yes')
            dispositivos = dispositivos.filter(activo=activo_bool)
        
        # Ordenar por última actualización
        dispositivos = dispositivos.order_by('-ultima_actualizacion')
        
        serializer = DispositivoUsuarioSerializer(dispositivos, many=True)
        
        return Response({
            'success': True,
            'count': dispositivos.count(),
            'dispositivos': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': f'Error al listar dispositivos: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_dispositivo_inactivo(request):
    """
    Marca un dispositivo como inactivo (sin eliminarlo)
    
    Útil para desactivar notificaciones temporalmente
    
    POST /notificaciones/api/marcar-inactivo/
    Body: {
        "token": "token_fcm_aqui"
    }
    """
    try:
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'error': 'El token es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dispositivo = DispositivoUsuario.objects.filter(
            usuario=request.user,
            token_fcm=token
        ).first()
        
        if dispositivo:
            dispositivo.marcar_como_inactivo()
            return Response({
                'success': True,
                'message': 'Dispositivo marcado como inactivo'
            })
        else:
            return Response({
                'success': False,
                'message': 'Dispositivo no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response(
            {'error': f'Error al marcar dispositivo: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─────────────────────────────────────────────────────────
# NUEVAS VISTAS: Panel de gestión y envío manual
# ─────────────────────────────────────────────────────────

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json


@staff_member_required
def panel_notificaciones(request):
    """
    Panel de administración de notificaciones.
    Solo accesible por staff.
    GET /notificaciones/panel/
    """
    from .scheduler import listar_tareas
    from .models import Notificacion
    from django.contrib.auth import get_user_model
    User = get_user_model()

    tareas = listar_tareas()
    ultimas = Notificacion.objects.select_related('usuario').order_by('-fecha_envio')[:20]
    total_usuarios = User.objects.filter(is_active=True).count()
    dispositivos_activos = DispositivoUsuario.objects.filter(activo=True).count()

    categorias = [
        {"id": "desayuno",    "emoji": "🍳", "nombre": "Desayuno"},
        {"id": "media_manana","emoji": "🍎", "nombre": "Media mañana"},
        {"id": "almuerzo",    "emoji": "🍽️", "nombre": "Almuerzo"},
        {"id": "merienda",    "emoji": "🫐", "nombre": "Merienda"},
        {"id": "cena",        "emoji": "🌙", "nombre": "Cena"},
        {"id": "agua",        "emoji": "💧", "nombre": "Hidratación"},
        {"id": "actividad",   "emoji": "📅", "nombre": "Actividad"},
        {"id": "seguimiento", "emoji": "📊", "nombre": "Seguimiento"},
        {"id": "registro",    "emoji": "📝", "nombre": "Registro comida"},
        {"id": "receta",      "emoji": "🍜", "nombre": "Nueva receta"},
        {"id": "motivacion",  "emoji": "💚", "nombre": "Motivación"},
        {"id": "resumen",     "emoji": "📈", "nombre": "Resumen diario"},
    ]

    context = {
        'tareas': tareas,
        'ultimas_notificaciones': ultimas,
        'total_usuarios': total_usuarios,
        'dispositivos_activos': dispositivos_activos,
        'categorias': categorias,
    }
    return render(request, 'notificacion/panel_admin.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enviar_notificacion_manual(request):
    """
    Envía una notificación de una categoría específica.
    Solo staff puede enviar a otros usuarios; usuarios normales solo a sí mismos.

    POST /notificaciones/api/enviar-manual/
    Body: {
        "categoria": "motivacion",
        "usuario_id": 5,          // Opcional — solo staff puede especificar otro usuario
        "nombre_actividad": "...", // Opcional para categoría 'actividad'
        "nombre_receta": "...",    // Opcional para categoría 'receta'
        "broadcast": false         // true = enviar a TODOS (solo staff)
    }
    """
    from .tasks import enviar_notificacion_personalizada

    categoria = request.data.get('categoria')
    broadcast = request.data.get('broadcast', False)
    nombre_actividad = request.data.get('nombre_actividad', '')
    nombre_receta = request.data.get('nombre_receta', '')

    CATEGORIAS_VALIDAS = [
        "desayuno", "media_manana", "almuerzo", "merienda", "cena",
        "agua", "actividad", "seguimiento", "registro",
        "receta", "motivacion", "resumen"
    ]

    if not categoria or categoria not in CATEGORIAS_VALIDAS:
        return Response(
            {'error': f'Categoría inválida. Opciones: {CATEGORIAS_VALIDAS}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Broadcast: solo staff
    if broadcast:
        if not request.user.is_staff:
            return Response({'error': 'Solo el staff puede hacer broadcast'}, status=status.HTTP_403_FORBIDDEN)

        from .services import enviar_notificacion_a_multiples_usuarios
        from .tasks import (
            tarea_recordatorio_desayuno, tarea_recordatorio_media_manana,
            tarea_recordatorio_almuerzo, tarea_recordatorio_merienda,
            tarea_recordatorio_cena, tarea_recordatorio_agua,
            tarea_motivacion, tarea_resumen_diario, tarea_nueva_receta,
        )
        # Ejecutar la tarea broadcast directamente
        BROADCAST_MAP = {
            "desayuno": tarea_recordatorio_desayuno,
            "media_manana": tarea_recordatorio_media_manana,
            "almuerzo": tarea_recordatorio_almuerzo,
            "merienda": tarea_recordatorio_merienda,
            "cena": tarea_recordatorio_cena,
            "agua": tarea_recordatorio_agua,
            "motivacion": tarea_motivacion,
            "resumen": tarea_resumen_diario,
            "receta": tarea_nueva_receta,
        }
        if categoria in BROADCAST_MAP:
            BROADCAST_MAP[categoria]()
            return Response({'success': True, 'message': f'Broadcast de {categoria} ejecutado'})
        else:
            return Response({'error': f'Broadcast no disponible para {categoria}'}, status=400)

    # Envío a usuario específico
    usuario_id = request.data.get('usuario_id', request.user.id)
    if int(usuario_id) != request.user.id and not request.user.is_staff:
        return Response({'error': 'No tienes permiso para enviar a otros usuarios'}, status=status.HTTP_403_FORBIDDEN)

    resultado = enviar_notificacion_personalizada(
        usuario_id=int(usuario_id),
        categoria=categoria,
        nombre_actividad=nombre_actividad,
        nombre_receta=nombre_receta,
    )

    return Response({
        'success': True,
        'categoria': categoria,
        'resultado': resultado
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estado_scheduler(request):
    """
    Retorna el estado actual del scheduler y sus tareas.
    GET /notificaciones/api/scheduler/
    """
    if not request.user.is_staff:
        return Response({'error': 'Solo staff'}, status=status.HTTP_403_FORBIDDEN)

    from .scheduler import listar_tareas, get_scheduler
    scheduler = get_scheduler()
    return Response({
        'corriendo': scheduler.running if scheduler else False,
        'tareas': listar_tareas(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def diagnostico_token(request):
    """
    Envía una notificación de prueba al usuario autenticado y muestra
    el resultado detallado. Útil para debuggear por qué no llegan.

    POST /notificaciones/api/diagnostico/
    """
    if not request.user.is_staff:
        return Response({'error': 'Solo staff'}, status=status.HTTP_403_FORBIDDEN)

    from firebase_admin import messaging as fb_messaging
    import firebase_admin

    # Verificar que Firebase esté inicializado
    firebase_ok = bool(firebase_admin._apps)

    dispositivos = DispositivoUsuario.objects.filter(
        usuario=request.user, activo=True
    )

    resultados_tokens = []
    for d in dispositivos:
        token_preview = d.token_fcm[:30] + '...' if len(d.token_fcm) > 30 else d.token_fcm
        try:
            # Envío de prueba mínimo
            msg = fb_messaging.Message(
                data={'title': '🔔 Prueba NutriET', 'body': 'Si ves esto, las notificaciones funcionan ✅'},
                token=d.token_fcm,
                webpush=fb_messaging.WebpushConfig(headers={'TTL': '60'}),
            )
            resp = fb_messaging.send(msg)
            resultados_tokens.append({
                'dispositivo': d.nombre_dispositivo,
                'token_preview': token_preview,
                'activo': d.activo,
                'resultado': 'OK',
                'message_id': resp,
            })
        except fb_messaging.UnregisteredError:
            d.marcar_como_inactivo()
            resultados_tokens.append({
                'dispositivo': d.nombre_dispositivo,
                'token_preview': token_preview,
                'activo': False,
                'resultado': 'ERROR: Token inválido/expirado — marcado inactivo',
            })
        except Exception as e:
            resultados_tokens.append({
                'dispositivo': d.nombre_dispositivo,
                'token_preview': token_preview,
                'activo': d.activo,
                'resultado': f'ERROR: {str(e)}',
            })

    return Response({
        'firebase_inicializado': firebase_ok,
        'usuario': request.user.username,
        'total_dispositivos_activos': dispositivos.count(),
        'tokens': resultados_tokens,
        'instruccion': 'Si todos los tokens dicen OK pero no llega nada, el problema es el Service Worker en el navegador. Abre DevTools > Application > Service Workers y haz Update.',
    })