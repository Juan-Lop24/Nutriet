# applications/notificacion/views.py

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
    Guarda o actualiza el Player ID de OneSignal del usuario.
    El campo sigue llamándose token_fcm en BD por compatibilidad.

    POST /notificaciones/api/guardar-token-fcm/
    Body: {
        "token": "player-id-de-onesignal",
        "nombre_dispositivo": "Chrome - Windows",
        "sistema_operativo": "Web"
    }
    """
    try:
        token = request.data.get('token')
        nombre_dispositivo = request.data.get('nombre_dispositivo', 'Dispositivo Web')
        sistema_operativo  = request.data.get('sistema_operativo', 'Web')

        if not token:
            return Response({'error': 'El token es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        # Desactivar tokens anteriores del mismo usuario/SO
        DispositivoUsuario.objects.filter(
            usuario=request.user,
            sistema_operativo=sistema_operativo,
            activo=True,
        ).exclude(token_fcm=token).update(activo=False)

        dispositivo, created = DispositivoUsuario.objects.update_or_create(
            usuario=request.user,
            token_fcm=token,
            defaults={
                'nombre_dispositivo': nombre_dispositivo,
                'sistema_operativo': sistema_operativo,
                'activo': True,
            }
        )

        serializer = DispositivoUsuarioSerializer(dispositivo)
        mensaje = 'Player ID guardado' if created else 'Player ID actualizado'

        return Response({
            'success': True,
            'created': created,
            'message': mensaje,
            'dispositivo': serializer.data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': f'Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_token_fcm(request):
    try:
        token = request.data.get('token')
        if not token:
            return Response({'error': 'El token es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        dispositivos = DispositivoUsuario.objects.filter(usuario=request.user, token_fcm=token)
        if dispositivos.exists():
            count = dispositivos.count()
            dispositivos.delete()
            return Response({'success': True, 'message': f'{count} dispositivo(s) eliminado(s)'})
        return Response({'success': False, 'message': 'No se encontró el dispositivo'}, status=404)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_dispositivos(request):
    try:
        dispositivos = DispositivoUsuario.objects.filter(usuario=request.user)
        activo = request.query_params.get('activo')
        if activo is not None:
            dispositivos = dispositivos.filter(activo=activo.lower() in ('true', '1', 'yes'))
        dispositivos = dispositivos.order_by('-ultima_actualizacion')
        serializer = DispositivoUsuarioSerializer(dispositivos, many=True)
        return Response({'success': True, 'count': dispositivos.count(), 'dispositivos': serializer.data})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_dispositivo_inactivo(request):
    try:
        token = request.data.get('token')
        if not token:
            return Response({'error': 'El token es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        dispositivo = DispositivoUsuario.objects.filter(usuario=request.user, token_fcm=token).first()
        if dispositivo:
            dispositivo.marcar_como_inactivo()
            return Response({'success': True, 'message': 'Dispositivo marcado como inactivo'})
        return Response({'success': False, 'message': 'No encontrado'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── Panel y envío manual ──────────────────────────────────────────────────────

from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@staff_member_required
def panel_notificaciones(request):
    from .scheduler import listar_tareas
    from .models import Notificacion
    from django.contrib.auth import get_user_model
    User = get_user_model()

    categorias = [
        {"id": "desayuno",    "emoji": "🍳",  "nombre": "Desayuno"},
        {"id": "media_manana","emoji": "🍎",  "nombre": "Media mañana"},
        {"id": "almuerzo",    "emoji": "🍽️", "nombre": "Almuerzo"},
        {"id": "merienda",    "emoji": "🫐",  "nombre": "Merienda"},
        {"id": "cena",        "emoji": "🌙",  "nombre": "Cena"},
        {"id": "agua",        "emoji": "💧",  "nombre": "Hidratación"},
        {"id": "actividad",   "emoji": "📅",  "nombre": "Actividad"},
        {"id": "seguimiento", "emoji": "📊",  "nombre": "Seguimiento"},
        {"id": "registro",    "emoji": "📝",  "nombre": "Registro comida"},
        {"id": "receta",      "emoji": "🍜",  "nombre": "Nueva receta"},
        {"id": "motivacion",  "emoji": "💚",  "nombre": "Motivación"},
        {"id": "resumen",     "emoji": "📈",  "nombre": "Resumen diario"},
    ]

    return render(request, 'notificacion/panel_admin.html', {
        'tareas': listar_tareas(),
        'ultimas_notificaciones': Notificacion.objects.select_related('usuario').order_by('-fecha_envio')[:20],
        'total_usuarios': User.objects.filter(is_active=True).count(),
        'dispositivos_activos': DispositivoUsuario.objects.filter(activo=True).count(),
        'categorias': categorias,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enviar_notificacion_manual(request):
    from .tasks import enviar_notificacion_personalizada

    categoria       = request.data.get('categoria')
    broadcast       = request.data.get('broadcast', False)
    nombre_actividad = request.data.get('nombre_actividad', '')
    nombre_receta   = request.data.get('nombre_receta', '')

    CATEGORIAS_VALIDAS = [
        "desayuno", "media_manana", "almuerzo", "merienda", "cena",
        "agua", "actividad", "seguimiento", "registro",
        "receta", "motivacion", "resumen"
    ]

    if not categoria or categoria not in CATEGORIAS_VALIDAS:
        return Response({'error': f'Categoría inválida. Opciones: {CATEGORIAS_VALIDAS}'}, status=400)

    if broadcast:
        if not request.user.is_staff:
            return Response({'error': 'Solo el staff puede hacer broadcast'}, status=403)

        from .tasks import (
            tarea_recordatorio_desayuno, tarea_recordatorio_media_manana,
            tarea_recordatorio_almuerzo, tarea_recordatorio_merienda,
            tarea_recordatorio_cena, tarea_recordatorio_agua,
            tarea_motivacion, tarea_resumen_diario, tarea_nueva_receta,
        )
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
        return Response({'error': f'Broadcast no disponible para {categoria}'}, status=400)

    usuario_id = request.data.get('usuario_id', request.user.id)
    if int(usuario_id) != request.user.id and not request.user.is_staff:
        return Response({'error': 'No tienes permiso'}, status=403)

    resultado = enviar_notificacion_personalizada(
        usuario_id=int(usuario_id),
        categoria=categoria,
        nombre_actividad=nombre_actividad,
        nombre_receta=nombre_receta,
    )
    return Response({'success': True, 'categoria': categoria, 'resultado': resultado})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estado_scheduler(request):
    if not request.user.is_staff:
        return Response({'error': 'Solo staff'}, status=403)
    from .scheduler import listar_tareas, get_scheduler
    scheduler = get_scheduler()
    return Response({'corriendo': scheduler.running if scheduler else False, 'tareas': listar_tareas()})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def diagnostico_token(request):
    """
    Diagnóstico de tokens OneSignal: envía notificación de prueba
    usando la API REST de OneSignal.
    """
    if not request.user.is_staff:
        return Response({'error': 'Solo staff'}, status=403)

    from django.conf import settings
    import requests as req_lib

    onesignal_ok = bool(
        getattr(settings, 'ONESIGNAL_APP_ID', None) and
        getattr(settings, 'ONESIGNAL_REST_KEY', None)
    )

    dispositivos = DispositivoUsuario.objects.filter(usuario=request.user, activo=True)
    resultados_tokens = []

    for d in dispositivos:
        token_preview = d.token_fcm[:30] + '...' if len(d.token_fcm) > 30 else d.token_fcm
        try:
            payload = {
                "app_id": settings.ONESIGNAL_APP_ID,
                "include_player_ids": [d.token_fcm],
                "headings": {"en": "🔔 Prueba NutriET"},
                "contents": {"en": "Si ves esto, las notificaciones funcionan ✅"},
            }
            resp = req_lib.post(
                "https://onesignal.com/api/v1/notifications",
                json=payload,
                headers={
                    "Authorization": f"Basic {settings.ONESIGNAL_REST_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            data = resp.json()

            if resp.ok and not data.get('errors'):
                resultado = 'OK'
            elif 'InvalidPlayerIds' in str(data.get('errors', '')):
                d.marcar_como_inactivo()
                resultado = 'ERROR: Player ID inválido — marcado inactivo'
            else:
                resultado = f'ERROR: {data}'

            resultados_tokens.append({
                'dispositivo': d.nombre_dispositivo,
                'token_preview': token_preview,
                'activo': d.activo,
                'resultado': resultado,
            })
        except Exception as e:
            resultados_tokens.append({
                'dispositivo': d.nombre_dispositivo,
                'token_preview': token_preview,
                'activo': d.activo,
                'resultado': f'ERROR: {str(e)}',
            })

    return Response({
        'onesignal_configurado': onesignal_ok,
        'usuario': request.user.username,
        'total_dispositivos_activos': dispositivos.count(),
        'tokens': resultados_tokens,
        'instruccion': 'Si todos dicen OK pero no llega nada, verifica que el OneSignalSDKWorker.js esté en la raíz del dominio.',
    })
