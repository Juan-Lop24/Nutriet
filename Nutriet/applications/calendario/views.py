import json
import logging
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from .models import Actividad
from Nutriet.utils import verificar_formulario_completo
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@never_cache
@login_required
@verificar_formulario_completo
def calendario_view(request):
    return render(request, 'calendario.html')


def obtener_eventos(request):

    eventos = Actividad.objects.filter(usuario=request.user)

    data = []
    for e in eventos:
        if e.hora:
            start = f"{e.fecha.isoformat()}T{e.hora.strftime('%H:%M')}"
        else:
            start = e.fecha.isoformat()

        data.append({
            "id": e.id,
            "title": e.titulo,
            "start": start
        })

    return JsonResponse(data, safe=False)



def _enviar_notif_confirmacion(usuario_id, titulo_evento, fecha_str, hora_str=None):
    """Notifica al usuario que su actividad fue guardada."""
    try:
        from applications.notificacion.services import enviar_notificacion_a_usuario
        if hora_str:
            msg = f"'{titulo_evento}' guardado para el {fecha_str} a las {hora_str}. Te avisaremos 15 min antes."
        else:
            msg = f"'{titulo_evento}' guardado para el {fecha_str}."
        enviar_notificacion_a_usuario(
            usuario_id=usuario_id,
            titulo="✅ Actividad guardada",
            mensaje=msg,
            data={'tipo': 'actividad_guardada', 'nombre': titulo_evento},
            link='/calendario/',
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar notif confirmacion a usuario {usuario_id}: {e}")


@csrf_exempt
def agregar_evento(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "JSON inválido"}, status=400)

    titulo = data.get('title', '').strip()
    fecha = data.get('date', '').strip()
    hora_str = data.get('time')

    if not titulo or not fecha:
        return JsonResponse({"error": "Título y fecha son obligatorios"}, status=400)

    hora = None
    hora_display = None
    if hora_str:
        hora_str = hora_str.strip()
        try:
            if "AM" in hora_str or "PM" in hora_str:
                hora = datetime.strptime(hora_str, "%I:%M %p").time()
            else:
                hora = datetime.strptime(hora_str, "%H:%M").time()
            hora_display = hora.strftime("%H:%M")
        except ValueError:
            logger.warning(f"Formato de hora inválido: {hora_str}")

    actividad = Actividad.objects.create(
        titulo=titulo,
        fecha=fecha,
        hora=hora,
        usuario=request.user
    )

    # Notificación de confirmación inmediata
    if request.user.is_authenticated:
        _enviar_notif_confirmacion(
            usuario_id=request.user.id,
            titulo_evento=titulo,
            fecha_str=fecha,
            hora_str=hora_display,
        )

    return JsonResponse({"id": actividad.id, "ok": True})


@csrf_exempt
def editar_evento(request, evento_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "JSON inválido"}, status=400)

    actividad = get_object_or_404(Actividad, id=evento_id, usuario=request.user)


    if request.user.is_authenticated and actividad.usuario and actividad.usuario != request.user:
        return JsonResponse({"error": "Sin permiso"}, status=403)

    actividad.titulo = data.get('title', actividad.titulo).strip()
    hora_str = data.get('time')
    if hora_str:
        try:
            actividad.hora = datetime.strptime(hora_str.strip(), "%H:%M").time()
        except ValueError:
            pass
    # Resetear flag para que el scheduler reenvíe notificación si corresponde
    actividad.notificacion_enviada = False
    actividad.save()

    return JsonResponse({"message": "Evento actualizado", "ok": True})


@csrf_exempt
def eliminar_evento(request, evento_id):
    if request.method != 'DELETE':
        return HttpResponseNotAllowed(['DELETE'])

    actividad = get_object_or_404(Actividad, id=evento_id, )

    if request.user.is_authenticated and actividad.usuario and actividad.usuario != request.user:
        return JsonResponse({"error": "Sin permiso"}, status=403)

    actividad.delete()
    return JsonResponse({"message": "Evento eliminado", "ok": True})
