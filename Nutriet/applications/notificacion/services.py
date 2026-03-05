# applications/notificacion/services.py
"""
Servicios para enviar notificaciones push con Firebase Cloud Messaging.

ESTRATEGIA DE PAYLOAD:
- Se envía SOLO data payload (sin notification payload a nivel raíz).
- Esto garantiza que el Service Worker siempre tenga control total y muestre
  la notificación con showNotification(). Si se manda notification + data juntos,
  Chrome Web puede manejarla automáticamente y descartarla silenciosamente cuando
  hay campos inválidos (badge, link sin HTTPS, etc.).
- El SW extrae title/body del campo data.
"""

from firebase_admin import messaging
from .models import DispositivoUsuario, Notificacion
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


def enviar_notificacion_a_usuario(usuario_id, titulo, mensaje, data=None, imagen_url=None, link=None):
    """
    Envía notificación push a todos los dispositivos activos del usuario.

    Returns:
        dict: { 'exitosas': int, 'fallidas': int, 'tokens_invalidos': [], 'errores': [] }
    """
    try:
        usuario = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        return {'exitosas': 0, 'fallidas': 0, 'error': 'Usuario no encontrado'}

    dispositivos = DispositivoUsuario.objects.filter(usuario=usuario, activo=True)

    if not dispositivos.exists():
        return {'exitosas': 0, 'fallidas': 0, 'error': 'Usuario no tiene dispositivos activos'}

    resultados = {'exitosas': 0, 'fallidas': 0, 'tokens_invalidos': [], 'errores': []}

    # Construir datos — todos los valores DEBEN ser strings (requisito de FCM)
    # Nunca mutar el dict original que viene como argumento
    datos_extra = {}
    if data:
        for k, v in data.items():
            datos_extra[str(k)] = str(v)

    # Incluir título y body en data para que el SW los pueda leer
    datos_extra['title'] = str(titulo)
    datos_extra['body'] = str(mensaje)
    if link:
        datos_extra['url'] = str(link)
    if imagen_url:
        datos_extra['image'] = str(imagen_url)

    for dispositivo in dispositivos:
        try:
            # ── Enviamos SOLO data payload, sin notification ──────────────────
            # Esto obliga al SW a manejar la notificación vía onBackgroundMessage,
            # dándonos control total sobre cómo se muestra.
            message = messaging.Message(
                data=datos_extra,
                token=dispositivo.token_fcm,

                # Webpush: solo config básica, sin link (requiere HTTPS)
                webpush=messaging.WebpushConfig(
                    headers={'TTL': '86400'},  # Guardar hasta 24h si el dispositivo está offline
                ),

                # Android: prioridad alta para que despierte la app
                android=messaging.AndroidConfig(
                    priority='high',
                ),
            )

            response = messaging.send(message)

            # Registrar éxito en BD
            Notificacion.objects.create(
                usuario=usuario,
                titulo=titulo,
                cuerpo=mensaje,
                imagen_url=imagen_url,
                datos_adicionales=datos_extra,
                estado='enviada',
                respuesta_firebase=response
            )

            resultados['exitosas'] += 1
            print(f"✅ Notificación enviada a {dispositivo.nombre_dispositivo}: {response}")

        except messaging.UnregisteredError:
            dispositivo.marcar_como_inactivo()
            resultados['tokens_invalidos'].append(dispositivo.token_fcm)
            resultados['fallidas'] += 1
            print(f"❌ Token inválido: {dispositivo.nombre_dispositivo}")

        except messaging.SenderIdMismatchError:
            dispositivo.marcar_como_inactivo()
            resultados['tokens_invalidos'].append(dispositivo.token_fcm)
            resultados['fallidas'] += 1
            print(f"❌ Token de otro proyecto: {dispositivo.nombre_dispositivo}")

        except Exception as e:
            resultados['fallidas'] += 1
            resultados['errores'].append(str(e))
            print(f"❌ Error enviando a {dispositivo.nombre_dispositivo}: {e}")

            Notificacion.objects.create(
                usuario=usuario,
                titulo=titulo,
                cuerpo=mensaje,
                imagen_url=imagen_url,
                datos_adicionales=datos_extra,
                estado='error',
                respuesta_firebase=str(e)
            )

    return resultados


def enviar_notificacion_a_multiples_usuarios(usuarios_ids, titulo, mensaje, data=None, imagen_url=None, link=None):
    resultados = {
        'usuarios_procesados': 0,
        'total_exitosas': 0,
        'total_fallidas': 0,
        'total_tokens_invalidos': 0
    }
    for usuario_id in usuarios_ids:
        resultado = enviar_notificacion_a_usuario(
            usuario_id=usuario_id, titulo=titulo, mensaje=mensaje,
            data=data, imagen_url=imagen_url, link=link
        )
        if 'error' not in resultado:
            resultados['usuarios_procesados'] += 1
            resultados['total_exitosas'] += resultado.get('exitosas', 0)
            resultados['total_fallidas'] += resultado.get('fallidas', 0)
            resultados['total_tokens_invalidos'] += len(resultado.get('tokens_invalidos', []))
    return resultados


def enviar_notificacion_broadcast(titulo, mensaje, data=None, imagen_url=None, link=None, filtro=None):
    if filtro:
        usuarios = User.objects.filter(filtro).values_list('id', flat=True)
    else:
        usuarios = User.objects.filter(is_active=True).values_list('id', flat=True)
    return enviar_notificacion_a_multiples_usuarios(
        usuarios_ids=list(usuarios), titulo=titulo, mensaje=mensaje,
        data=data, imagen_url=imagen_url, link=link
    )


def limpiar_tokens_invalidos(dias_inactivo=30):
    fecha_limite = timezone.now() - timedelta(days=dias_inactivo)
    tokens_eliminados = DispositivoUsuario.objects.filter(
        activo=False, ultima_actualizacion__lt=fecha_limite
    ).delete()
    return tokens_eliminados[0]


def obtener_estadisticas_dispositivos():
    from django.db.models import Count
    por_so = list(
        DispositivoUsuario.objects.filter(activo=True)
        .values('sistema_operativo').annotate(count=Count('id'))
    )
    return {
        'total_dispositivos': DispositivoUsuario.objects.count(),
        'dispositivos_activos': DispositivoUsuario.objects.filter(activo=True).count(),
        'dispositivos_inactivos': DispositivoUsuario.objects.filter(activo=False).count(),
        'por_sistema_operativo': por_so,
        'usuarios_con_notificaciones': (
            DispositivoUsuario.objects.filter(activo=True)
            .values('usuario').distinct().count()
        )
    }


# ─── Funciones de conveniencia ────────────────────────────────────────────────

def enviar_recordatorio_comida(usuario_id, comida="almuerzo"):
    from .copy_bank import get_copy_comida
    comida_key = comida.lower().replace(" ", "_").replace("á", "a").replace("é", "e")
    tipo_map = {
        "desayuno": "desayuno", "media_manana": "media_manana",
        "media mañana": "media_manana", "almuerzo": "almuerzo",
        "merienda": "merienda", "cena": "cena",
    }
    tipo = tipo_map.get(comida_key, "almuerzo")
    titulo, mensaje = get_copy_comida(tipo)
    return enviar_notificacion_a_usuario(
        usuario_id=usuario_id, titulo=titulo, mensaje=mensaje,
        data={'tipo': 'recordatorio_comida', 'comida': comida},
        link='/nutricion/formulario/'
    )


def enviar_notificacion_nueva_receta(usuario_id, receta_id, receta_titulo, receta_imagen=None):
    from .copy_bank import get_copy_receta
    titulo, mensaje = get_copy_receta(receta_titulo)
    return enviar_notificacion_a_usuario(
        usuario_id=usuario_id, titulo=titulo, mensaje=mensaje,
        data={'tipo': 'nueva_receta', 'receta_id': str(receta_id)},
        imagen_url=receta_imagen, link=f'/recetas/{receta_id}/'
    )


def enviar_felicitacion_meta(usuario_id, meta_alcanzada):
    return enviar_notificacion_a_usuario(
        usuario_id=usuario_id,
        titulo="🎉 ¡Felicitaciones!",
        mensaje=f"Has alcanzado tu meta: {meta_alcanzada}. ¡Eso es dedicación de verdad!",
        data={'tipo': 'meta_alcanzada', 'meta': meta_alcanzada},
        link='/seguimiento/tablero/'
    )


def enviar_motivacion(usuario_id):
    from .copy_bank import get_copy_motivacion
    titulo, mensaje = get_copy_motivacion()
    return enviar_notificacion_a_usuario(
        usuario_id=usuario_id, titulo=titulo, mensaje=mensaje,
        data={'tipo': 'motivacion'}, link='/seguimiento/tablero/'
    )


def enviar_recordatorio_agua(usuario_id):
    from .copy_bank import get_copy_hidratacion
    titulo, mensaje = get_copy_hidratacion()
    return enviar_notificacion_a_usuario(
        usuario_id=usuario_id, titulo=titulo, mensaje=mensaje,
        data={'tipo': 'recordatorio_agua'}, link='/'
    )
