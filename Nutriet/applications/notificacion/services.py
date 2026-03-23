# applications/notificacion/services.py
"""
Servicio de envío de notificaciones push vía OneSignal REST API.
Reemplaza completamente Firebase Cloud Messaging (FCM).
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ONESIGNAL_URL = "https://onesignal.com/api/v1/notifications"
SITE_URL = "https://nutrietcol.site"


def _url_absoluta(url: str) -> str:
    """Convierte una URL relativa en absoluta. OneSignal exige https://."""
    if not url:
        return SITE_URL
    if url.startswith(('http://', 'https://')):
        return url
    return SITE_URL + url


def _enviar_a_player_id(player_id: str, title: str, body: str, url: str = "/") -> dict:
    """
    Envía una notificación a un Player ID de OneSignal.
    Retorna dict con resultado.
    """
    if not getattr(settings, 'ONESIGNAL_APP_ID', None):
        logger.error("[OneSignal] ONESIGNAL_APP_ID no configurado")
        return {"ok": False, "error": "ONESIGNAL_APP_ID no configurado"}

    if not getattr(settings, 'ONESIGNAL_REST_KEY', None):
        logger.error("[OneSignal] ONESIGNAL_REST_KEY no configurado")
        return {"ok": False, "error": "ONESIGNAL_REST_KEY no configurado"}

    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "include_player_ids": [player_id],
        "headings": {"en": title, "es": title},
        "contents": {"en": body, "es": body},
        "web_url": _url_absoluta(url),
    }

    try:
        resp = requests.post(
            ONESIGNAL_URL,
            json=payload,
            headers={
                "Authorization": f"Basic {settings.ONESIGNAL_REST_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        data = resp.json()

        if resp.ok and not data.get("errors"):
            logger.debug("[OneSignal] OK → player_id=%s", player_id[:20])
            return {"ok": True, "id": data.get("id")}

        errors = data.get("errors", [])
        if "InvalidPlayerIds" in str(errors):
            return {"ok": False, "invalid": True, "error": str(errors)}

        logger.warning("[OneSignal] Error respuesta: %s", data)
        return {"ok": False, "error": str(errors)}

    except requests.Timeout:
        logger.error("[OneSignal] Timeout enviando a %s", player_id[:20])
        return {"ok": False, "error": "timeout"}
    except Exception as exc:
        logger.error("[OneSignal] Excepción: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── API pública ────────────────────────────────────────────────────────────────

def enviar_notificacion_a_usuario(
    usuario=None,
    titulo: str = "",
    cuerpo: str = "",
    url: str = "/",
    # Aliases usados en tasks.py y calendario/views.py
    usuario_id=None,
    mensaje: str = "",
    link: str = None,
    data: dict = None,
) -> dict:
    """
    Envía notificación a todos los dispositivos activos de un usuario.
    Acepta tanto (usuario, titulo, cuerpo, url)
    como  (usuario_id, titulo, mensaje, link, data).
    """
    from django.contrib.auth import get_user_model
    from .models import DispositivoUsuario

    # Resolver aliases
    if usuario is None and usuario_id is not None:
        try:
            usuario = get_user_model().objects.get(pk=usuario_id)
        except get_user_model().DoesNotExist:
            logger.warning("[OneSignal] Usuario id=%s no existe", usuario_id)
            return {"enviados": 0, "errores": 0}

    if not cuerpo and mensaje:
        cuerpo = mensaje

    if link is not None:
        url = link

    if usuario is None:
        logger.error("[OneSignal] Se llamó sin usuario ni usuario_id")
        return {"enviados": 0, "errores": 0}

    dispositivos = DispositivoUsuario.objects.filter(usuario=usuario, activo=True)

    if not dispositivos.exists():
        logger.info("[OneSignal] Usuario %s sin dispositivos activos", usuario.id)
        return {"enviados": 0, "errores": 0}

    enviados = 0
    errores = 0

    for dispositivo in dispositivos:
        resultado = _enviar_a_player_id(dispositivo.token_fcm, titulo, cuerpo, url)
        if resultado.get("ok"):
            enviados += 1
        else:
            errores += 1
            if resultado.get("invalid"):
                dispositivo.marcar_como_inactivo()

    return {"enviados": enviados, "errores": errores}


def enviar_notificacion_a_multiples_usuarios(usuarios, titulo: str, cuerpo: str, url: str = "/") -> dict:
    """
    Envía notificación a una lista de usuarios.
    """
    total_enviados = 0
    total_errores  = 0

    for usuario in usuarios:
        resultado = enviar_notificacion_a_usuario(usuario, titulo, cuerpo, url)
        total_enviados += resultado.get("enviados", 0)
        total_errores  += resultado.get("errores", 0)

    logger.info(
        "[OneSignal] Broadcast → %d enviados, %d errores (sobre %d usuarios)",
        total_enviados, total_errores, len(list(usuarios))
    )
    return {"enviados": total_enviados, "errores": total_errores}


def enviar_notificacion_broadcast(titulo: str, cuerpo: str, url: str = "/") -> dict:
    """
    Envía notificación a TODOS los usuarios con dispositivo activo.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    from .models import DispositivoUsuario
    usuario_ids = (
        DispositivoUsuario.objects
        .filter(activo=True)
        .values_list("usuario_id", flat=True)
        .distinct()
    )
    usuarios = User.objects.filter(id__in=usuario_ids, is_active=True)
    return enviar_notificacion_a_multiples_usuarios(usuarios, titulo, cuerpo, url)