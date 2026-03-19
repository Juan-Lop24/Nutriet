import json
import logging
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from .models import Actividad
from Nutriet.utils import verificar_formulario_completo
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

# ✅ FIX: eliminado el import de csrf_exempt — ya no se usa en ningún endpoint

logger = logging.getLogger(__name__)


@never_cache
@login_required
@verificar_formulario_completo
def calendario_view(request):
    return render(request, 'calendario.html')


@never_cache
@login_required
def obtener_eventos(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False)

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

    response = JsonResponse(data, safe=False)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Vary'] = 'Cookie'
    return response


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


# ✅ FIX: eliminado @csrf_exempt en los 3 endpoints de escritura.
# El frontend debe enviar el header X-CSRFToken en cada fetch().
# Ver instrucciones de JS al final de este archivo.

@login_required
def agregar_evento(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "JSON inválido"}, status=400)

    titulo   = data.get('title', '').strip()
    fecha    = data.get('date', '').strip()
    hora_str = data.get('time')

    if not titulo or not fecha:
        return JsonResponse({"error": "Título y fecha son obligatorios"}, status=400)

    # ✅ FIX: limitar longitud del título para evitar spam / datos grandes
    if len(titulo) > 200:
        return JsonResponse({"error": "El título es demasiado largo"}, status=400)

    hora         = None
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

    _enviar_notif_confirmacion(
        usuario_id=request.user.id,
        titulo_evento=titulo,
        fecha_str=fecha,
        hora_str=hora_display,
    )

    return JsonResponse({"id": actividad.id, "ok": True})


@login_required
def editar_evento(request, evento_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "JSON inválido"}, status=400)

    actividad = get_object_or_404(Actividad, id=evento_id, usuario=request.user)

    titulo_nuevo = data.get('title', actividad.titulo).strip()
    if len(titulo_nuevo) > 200:
        return JsonResponse({"error": "El título es demasiado largo"}, status=400)

    actividad.titulo = titulo_nuevo
    hora_str = data.get('time')
    if hora_str:
        try:
            actividad.hora = datetime.strptime(hora_str.strip(), "%H:%M").time()
        except ValueError:
            pass
    actividad.notificacion_enviada = False
    actividad.save()

    return JsonResponse({"message": "Evento actualizado", "ok": True})


@login_required
def eliminar_evento(request, evento_id):
    if request.method != 'DELETE':
        return HttpResponseNotAllowed(['DELETE'])

    actividad = get_object_or_404(Actividad, id=evento_id, usuario=request.user)
    actividad.delete()
    return JsonResponse({"message": "Evento eliminado", "ok": True})


# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUCCIONES PARA EL JAVASCRIPT DEL CALENDARIO
# ═══════════════════════════════════════════════════════════════════════════════
#
# Al eliminar @csrf_exempt, el frontend DEBE enviar el token CSRF en cada fetch.
# Agrega esta función utilitaria en tu calendario.html o en el JS del calendario:
#
#   function getCookie(name) {
#       const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
#       return v ? v[2] : null;
#   }
#
# Y en cada fetch de POST/DELETE, agrega el header:
#
#   fetch('/calendario/agregar/', {
#       method: 'POST',
#       headers: {
#           'Content-Type': 'application/json',
#           'X-CSRFToken': getCookie('csrftoken'),   // ← ESTA LÍNEA
#       },
#       body: JSON.stringify({ title, date, time })
#   })
#
#   fetch(`/calendario/eliminar/${id}/`, {
#       method: 'DELETE',
#       headers: {
#           'X-CSRFToken': getCookie('csrftoken'),   // ← ESTA LÍNEA
#       }
#   })
# ═══════════════════════════════════════════════════════════════════════════════