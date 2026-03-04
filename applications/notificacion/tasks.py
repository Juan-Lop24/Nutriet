# applications/notificacion/tasks.py
"""
Tareas programadas de notificaciones para NutriET.
Usa APScheduler (sin Celery) para simplificar el setup.

Instalar:   pip install apscheduler
Ejecutar:   Las tareas se registran automáticamente al arrancar Django
            a través de apps.py → NotificacionConfig.ready()

Horarios por defecto (todos en hora local del servidor):
  - Desayuno:     7:30
  - Media mañana: 10:00
  - Almuerzo:     12:30
  - Merienda:     15:30
  - Cena:         19:00
  - Hidratación:  cada 2 horas entre 8am y 8pm
  - Resumen:      21:00
  - Motivación:   días aleatorios a las 9:00
"""

import logging
import random
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .services import enviar_notificacion_a_usuario
from .copy_bank import (
    get_copy_comida,
    get_copy_hidratacion,
    get_copy_actividad,
    get_copy_registro_progreso,
    get_copy_registro_comida,
    get_copy_receta,
    get_copy_motivacion,
    get_copy_resumen,
    get_copy_medicion_proxima,
    get_copy_medicion_hoy,
    get_copy_motivacion_progreso,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def _usuarios_con_dispositivos():
    """Retorna IDs de usuarios que tienen al menos un dispositivo activo."""
    from .models import DispositivoUsuario
    return list(
        DispositivoUsuario.objects
        .filter(activo=True)
        .values_list('usuario_id', flat=True)
        .distinct()
    )


def _enviar_a_todos(get_copy_fn, data_tipo: str, link: str = '/', **copy_kwargs):
    """
    Helper: envía la misma categoría de notificación a todos los usuarios activos.
    Cada usuario recibe una variante aleatoria del copy.
    """
    usuario_ids = _usuarios_con_dispositivos()
    enviadas = 0
    for uid in usuario_ids:
        try:
            titulo, mensaje = get_copy_fn(**copy_kwargs)
            enviar_notificacion_a_usuario(
                usuario_id=uid,
                titulo=titulo,
                mensaje=mensaje,
                data={'tipo': data_tipo},
                link=link,
            )
            enviadas += 1
        except Exception as e:
            logger.error(f"Error enviando notificación tipo {data_tipo} a usuario {uid}: {e}")
    logger.info(f"[{data_tipo}] Enviadas: {enviadas}/{len(usuario_ids)}")
    return enviadas


# ─────────────────────────────────────────────
# CAT 1 · Recordatorios de comidas
# ─────────────────────────────────────────────

def tarea_recordatorio_desayuno():
    logger.info("🍳 Ejecutando recordatorio desayuno")
    _enviar_a_todos(
        get_copy_fn=lambda: get_copy_comida("desayuno"),
        data_tipo="recordatorio_desayuno",
        link="/nutricion/formulario/",
    )


def tarea_recordatorio_media_manana():
    logger.info("🍎 Ejecutando recordatorio media mañana")
    _enviar_a_todos(
        get_copy_fn=lambda: get_copy_comida("media_manana"),
        data_tipo="recordatorio_media_manana",
        link="/nutricion/formulario/",
    )


def tarea_recordatorio_almuerzo():
    logger.info("🍽️ Ejecutando recordatorio almuerzo")
    _enviar_a_todos(
        get_copy_fn=lambda: get_copy_comida("almuerzo"),
        data_tipo="recordatorio_almuerzo",
        link="/nutricion/formulario/",
    )


def tarea_recordatorio_merienda():
    logger.info("🫐 Ejecutando recordatorio merienda")
    _enviar_a_todos(
        get_copy_fn=lambda: get_copy_comida("merienda"),
        data_tipo="recordatorio_merienda",
        link="/nutricion/formulario/",
    )


def tarea_recordatorio_cena():
    logger.info("🌙 Ejecutando recordatorio cena")
    _enviar_a_todos(
        get_copy_fn=lambda: get_copy_comida("cena"),
        data_tipo="recordatorio_cena",
        link="/nutricion/formulario/",
    )


# ─────────────────────────────────────────────
# CAT 2 · Hidratación
# ─────────────────────────────────────────────

def tarea_recordatorio_agua():
    logger.info("💧 Ejecutando recordatorio de hidratación")
    _enviar_a_todos(
        get_copy_fn=get_copy_hidratacion,
        data_tipo="recordatorio_agua",
        link="/",
    )


# ─────────────────────────────────────────────
# CAT 3 · Eventos de calendario y seguimiento
# ─────────────────────────────────────────────

def tarea_recordatorio_actividades_calendario():
    """
    Revisa el calendario y avisa SOLO al dueño de cada actividad que tiene eventos HOY.
    """
    try:
        from applications.calendario.models import Actividad
        from .models import DispositivoUsuario
        hoy = timezone.localdate()
        # Solo actividades con usuario asignado (excluye actividades huérfanas)
        actividades_hoy = Actividad.objects.filter(
            fecha=hoy,
            usuario__isnull=False,
        ).select_related('usuario')

        if not actividades_hoy.exists():
            logger.info("📅 Sin actividades en calendario para hoy")
            return

        enviadas = 0
        for actividad in actividades_hoy:
            uid = actividad.usuario_id
            # Verificar que el usuario tiene dispositivos activos
            if not DispositivoUsuario.objects.filter(usuario_id=uid, activo=True).exists():
                continue
            try:
                titulo, mensaje = get_copy_actividad(actividad.titulo)
                hora_str = actividad.hora.strftime("%H:%M") if actividad.hora else ""
                if hora_str:
                    mensaje = f"{mensaje} — hoy a las {hora_str}"
                enviar_notificacion_a_usuario(
                    usuario_id=uid,
                    titulo=titulo,
                    mensaje=mensaje,
                    data={'tipo': 'evento_calendario', 'actividad_id': str(actividad.id)},
                    link="/calendario/",
                )
                enviadas += 1
            except Exception as e:
                logger.error(f"Error notificando actividad {actividad.id} a usuario {uid}: {e}")

        logger.info(f"📅 Notificadas {enviadas} actividades del día")
    except Exception as e:
        logger.error(f"Error en tarea_recordatorio_actividades_calendario: {e}")


def tarea_recordatorio_registro_progreso():
    """Se ejecuta los lunes para recordar el chequeo semanal."""
    logger.info("📊 Ejecutando recordatorio de seguimiento semanal")
    _enviar_a_todos(
        get_copy_fn=get_copy_registro_progreso,
        data_tipo="recordatorio_seguimiento",
        link="/seguimiento/tablero/",
    )


def tarea_recordatorio_registro_comida():
    """Aviso nocturno por si no registró ninguna comida en el día."""
    try:
        from applications.nutricion.models import FormularioNutricionGuardado
        hoy = timezone.localdate()

        # Usuarios SIN registros hoy
        usuarios_con_registro = set(
            FormularioNutricionGuardado.objects
            .filter(creado__date=hoy)
            .values_list('usuario_id', flat=True)
        )
        todos = set(_usuarios_con_dispositivos())
        sin_registro = todos - usuarios_con_registro

        enviadas = 0
        for uid in sin_registro:
            try:
                titulo, mensaje = get_copy_registro_comida()
                enviar_notificacion_a_usuario(
                    usuario_id=uid,
                    titulo=titulo,
                    mensaje=mensaje,
                    data={'tipo': 'sin_registro_hoy'},
                    link="/nutricion/formulario/",
                )
                enviadas += 1
            except Exception as e:
                logger.error(f"Error en recordatorio registro a usuario {uid}: {e}")

        logger.info(f"📝 Recordatorio registro enviado a {enviadas} usuarios sin registro")
    except Exception as e:
        logger.error(f"Error en tarea_recordatorio_registro_comida: {e}")


# ─────────────────────────────────────────────
# CAT 4 · Recetas
# ─────────────────────────────────────────────

def tarea_nueva_receta():
    """Se ejecuta cada 3 días para promover una receta."""
    logger.info("🍜 Ejecutando notificación de nueva receta")
    _enviar_a_todos(
        get_copy_fn=get_copy_receta,
        data_tipo="nueva_receta",
        link="/",
    )


# ─────────────────────────────────────────────
# CAT 5 · Motivación
# ─────────────────────────────────────────────

def tarea_motivacion():
    """Motivación diaria (no toxica)."""
    logger.info("💚 Ejecutando notificación de motivación")
    _enviar_a_todos(
        get_copy_fn=get_copy_motivacion,
        data_tipo="motivacion",
        link="/seguimiento/tablero/",
    )


# ─────────────────────────────────────────────
# CAT 6 · Resumen diario
# ─────────────────────────────────────────────

def tarea_resumen_diario():
    """Resumen nocturno del progreso del día."""
    logger.info("📊 Ejecutando resumen diario")
    _enviar_a_todos(
        get_copy_fn=get_copy_resumen,
        data_tipo="resumen_diario",
        link="/seguimiento/tablero/",
    )


# ─────────────────────────────────────────────
# CAT 7 · Recordatorio de medición física
# ─────────────────────────────────────────────

def tarea_recordatorio_medicion():
    """
    Notifica a los usuarios según su PreferenciaMedicion:
    - 1 día antes de que llegue su fecha de medición → notificación preventiva
    - El mismo día que toca medir → notificación de acción
    Solo si aún no han registrado la medición del ciclo actual.
    """
    try:
        from applications.seguimiento.models import MedicionFisica, PreferenciaMedicion
        from django.utils import timezone

        ahora = timezone.now()
        hoy = ahora.date()
        manana = hoy + timedelta(days=1)

        # Iterar todos los usuarios con preferencia configurada
        preferencias = PreferenciaMedicion.objects.select_related('usuario').all()
        enviadas = 0

        for pref in preferencias:
            uid = pref.usuario_id
            # Verificar que el usuario tiene dispositivos activos
            from .models import DispositivoUsuario
            if not DispositivoUsuario.objects.filter(usuario_id=uid, activo=True).exists():
                continue

            # Obtener la última medición del usuario
            ultima = MedicionFisica.objects.filter(usuario_id=uid).order_by('-creado_en').first()

            if ultima:
                proxima = ultima.creado_en.date() + timedelta(days=pref.frecuencia_dias)
            else:
                # Nunca ha medido → notificar hoy
                proxima = hoy

            # Notificación el mismo día
            if proxima == hoy:
                titulo, mensaje = get_copy_medicion_hoy()
                enviar_notificacion_a_usuario(
                    usuario_id=uid,
                    titulo=titulo,
                    mensaje=mensaje,
                    data={'tipo': 'medicion_hoy'},
                    link='/seguimiento/tablero/',
                )
                enviadas += 1

            # Recordatorio preventivo un día antes
            elif proxima == manana:
                titulo, mensaje = get_copy_medicion_proxima()
                enviar_notificacion_a_usuario(
                    usuario_id=uid,
                    titulo=titulo,
                    mensaje=mensaje,
                    data={'tipo': 'medicion_proxima'},
                    link='/seguimiento/tablero/',
                )
                enviadas += 1

        logger.info(f"📏 Recordatorio medición enviado a {enviadas} usuarios")

    except Exception as e:
        logger.error(f"Error en tarea_recordatorio_medicion: {e}")


# ─────────────────────────────────────────────
# CAT 8 · Receta personalizada para el usuario
# ─────────────────────────────────────────────

def tarea_receta_personalizada():
    """
    Recomienda una receta del catálogo local adaptada a las restricciones/dieta
    del usuario. Solo envía martes o jueves (se llama desde el scheduler esos días).
    Usa el catálogo local (RecetaMealDB) para no depender de la API en tiempo real.
    """
    try:
        from applications.recetas.models import RecetaMealDB, ClasificacionReceta, RESTRICCION_KEYS
        from applications.nutricion.models import FormularioNutricionGuardado

        usuario_ids = _usuarios_con_dispositivos()
        enviadas = 0

        for uid in usuario_ids:
            try:
                # Obtener restricciones del usuario desde su último formulario guardado
                formulario = (
                    FormularioNutricionGuardado.objects
                    .filter(usuario_id=uid)
                    .order_by('-creado')
                    .first()
                )

                # Base de recetas clasificadas
                qs = (
                    RecetaMealDB.objects
                    .filter(clasificado=True, clasificacion__isnull=False)
                    .select_related('clasificacion')
                )

                # Aplicar restricciones si hay formulario
                if formulario:
                    condiciones_texto = getattr(formulario, 'condiciones_medicas', '') or ''
                    tipo_dieta = getattr(formulario, 'tipo_dieta', '') or ''

                    # Excluir por restricciones clínicas
                    TEXTO_A_RESTRICCION = {
                        "diabetes": "diabetes", "diabete": "diabetes",
                        "lactosa": "intolerancia_lactosa", "lacteo": "intolerancia_lactosa",
                        "celiaca": "celiaca", "celíaca": "celiaca", "gluten": "celiaca",
                        "maní": "alergia_mani", "mani": "alergia_mani",
                        "fructosa": "intolerancia_fructosa",
                        "hipertension": "hipertension", "hipertensión": "hipertension",
                        "colesterol": "hipercolesterolemia",
                        "huevo": "alergia_huevo",
                        "marisco": "alergia_marisco", "mariscos": "alergia_marisco",
                    }
                    t = condiciones_texto.lower()
                    restricciones = {v for k, v in TEXTO_A_RESTRICCION.items() if k in t}
                    for r in restricciones:
                        if r in RESTRICCION_KEYS:
                            qs = qs.exclude(**{f"clasificacion__{r}": True})

                    # Tipo de dieta
                    CARNES = ["Beef", "Chicken", "Lamb", "Pork", "Seafood"]
                    if tipo_dieta == "vegetariano":
                        qs = qs.exclude(categoria__in=CARNES)
                    elif tipo_dieta == "vegano":
                        qs = qs.exclude(categoria__in=CARNES)
                        qs = qs.exclude(clasificacion__intolerancia_lactosa=True)
                        qs = qs.exclude(clasificacion__alergia_huevo=True)

                # Elegir una receta aleatoria
                total = qs.count()
                if total == 0:
                    qs = RecetaMealDB.objects.filter(clasificado=True)
                    total = qs.count()

                if total > 0:
                    receta = qs[random.randint(0, total - 1)]
                    nombre_receta = receta.nombre_es or receta.nombre
                    titulo, mensaje = get_copy_receta(nombre_receta)
                    enviar_notificacion_a_usuario(
                        usuario_id=uid,
                        titulo=titulo,
                        mensaje=mensaje,
                        data={'tipo': 'receta_personalizada', 'meal_id': str(receta.meal_id)},
                        link='/recetas/',
                    )
                    enviadas += 1

            except Exception as e:
                logger.error(f"Error enviando receta personalizada a usuario {uid}: {e}")

        logger.info(f"🍜 Recetas personalizadas enviadas a {enviadas}/{len(usuario_ids)} usuarios")

    except Exception as e:
        logger.error(f"Error en tarea_receta_personalizada: {e}")


# ─────────────────────────────────────────────
# CAT 9 · Motivación con datos reales de progreso
# ─────────────────────────────────────────────

def tarea_motivacion_con_progreso():
    """
    Envía motivación personalizada usando el progreso real de mediciones del usuario.
    Si el usuario tiene suficientes datos, usa el copy con números.
    Si no, usa el copy genérico.
    Solo lunes, miércoles y viernes (controlado desde el scheduler).
    """
    try:
        from applications.seguimiento.models import MedicionFisica

        usuario_ids = _usuarios_con_dispositivos()
        enviadas = 0

        for uid in usuario_ids:
            try:
                dias_registrados = MedicionFisica.objects.filter(usuario_id=uid).count()

                if dias_registrados >= 2:
                    # Calcular progreso aproximado (max 100%)
                    # Objetivo por defecto: 30 mediciones = meta completa
                    objetivo = 30
                    progreso = min(100, round((dias_registrados / objetivo) * 100))
                    titulo, mensaje = get_copy_motivacion_progreso(
                        progreso=progreso,
                        dias=dias_registrados,
                    )
                else:
                    titulo, mensaje = get_copy_motivacion()

                enviar_notificacion_a_usuario(
                    usuario_id=uid,
                    titulo=titulo,
                    mensaje=mensaje,
                    data={'tipo': 'motivacion_progreso'},
                    link='/seguimiento/tablero/',
                )
                enviadas += 1

            except Exception as e:
                logger.error(f"Error enviando motivación con progreso a usuario {uid}: {e}")

        logger.info(f"💚 Motivación con progreso enviada a {enviadas}/{len(usuario_ids)} usuarios")

    except Exception as e:
        logger.error(f"Error en tarea_motivacion_con_progreso: {e}")


# ─────────────────────────────────────────────
# CAT 10 · Notificaciones de calendario por usuario y hora
# ─────────────────────────────────────────────

def tarea_notificaciones_calendario_tiempo_real():
    """
    Revisa actividades del calendario con hora asignada y envia la notificacion
    15 minutos ANTES de que comience el evento al usuario dueno del evento.
    Se ejecuta cada 15 minutos desde el scheduler.
    Bug fix: rango de minutos del dia (evita fallo en cruce de medianoche).
    Bug fix: solo notifica al dueno del evento, no a todos los usuarios.
    """
    try:
        from applications.calendario.models import Actividad
        from django.utils import timezone
        from .models import DispositivoUsuario

        ahora = timezone.localtime()
        hoy = ahora.date()

        desde_min = ahora.hour * 60 + ahora.minute
        hasta_dt = ahora + timedelta(minutes=15)
        hasta_min = hasta_dt.hour * 60 + hasta_dt.minute

        actividades = Actividad.objects.filter(
            fecha=hoy,
            hora__isnull=False,
            notificacion_enviada=False,
            usuario__isnull=False,
        ).select_related('usuario')

        enviadas = 0
        for actividad in actividades:
            hora_ev = actividad.hora
            minutos_evento = hora_ev.hour * 60 + hora_ev.minute

            # Manejar cruce de medianoche correctamente
            if hasta_min >= desde_min:
                en_ventana = desde_min <= minutos_evento <= hasta_min
            else:
                en_ventana = minutos_evento >= desde_min or minutos_evento <= hasta_min

            if not en_ventana:
                continue

            uid = actividad.usuario_id
            if not DispositivoUsuario.objects.filter(usuario_id=uid, activo=True).exists():
                continue

            hora_str = hora_ev.strftime("%H:%M")
            titulo, mensaje = get_copy_actividad(actividad.titulo)
            mensaje = f"{mensaje} — hoy a las {hora_str}"

            enviar_notificacion_a_usuario(
                usuario_id=uid,
                titulo=titulo,
                mensaje=mensaje,
                data={'tipo': 'evento_calendario_pronto', 'actividad_id': str(actividad.id)},
                link='/calendario/',
            )
            actividad.notificacion_enviada = True
            actividad.save(update_fields=['notificacion_enviada'])
            enviadas += 1

        if enviadas:
            logger.info(f"Notificaciones calendario enviadas: {enviadas}")

    except Exception as e:
        logger.error(f"Error en tarea_notificaciones_calendario_tiempo_real: {e}")



def tarea_reset_notificaciones_calendario():
    """
    Resetea el flag notificacion_enviada al inicio de cada día para que
    los eventos recurrentes puedan notificarse de nuevo.
    Se ejecuta a las 00:05 diariamente.
    """
    try:
        from applications.calendario.models import Actividad
        from django.utils import timezone

        ayer = timezone.localdate() - timedelta(days=1)
        Actividad.objects.filter(fecha__lte=ayer, notificacion_enviada=True).update(
            notificacion_enviada=False
        )
        logger.info("🔄 Flags de notificación de calendario reseteados")
    except Exception as e:
        logger.error(f"Error en tarea_reset_notificaciones_calendario: {e}")


# ─────────────────────────────────────────────

def enviar_notificacion_personalizada(usuario_id: int, categoria: str, **kwargs) -> dict:
    """
    Envía una notificación de una categoría específica a un usuario.

    Parámetros:
        usuario_id: ID del usuario destinatario
        categoria: 'desayuno' | 'media_manana' | 'almuerzo' | 'merienda' | 'cena'
                   'agua' | 'actividad' | 'seguimiento' | 'registro'
                   'receta' | 'motivacion' | 'resumen'
        **kwargs: argumentos opcionales según categoría
            - nombre_actividad (str): para categoría 'actividad'
            - nombre_receta (str): para categoría 'receta'

    Retorna dict de resultados de envío.
    """
    CATEGORIAS = {
        "desayuno":          (lambda: get_copy_comida("desayuno"),     "/nutricion/formulario/"),
        "media_manana":      (lambda: get_copy_comida("media_manana"), "/nutricion/formulario/"),
        "almuerzo":          (lambda: get_copy_comida("almuerzo"),     "/nutricion/formulario/"),
        "merienda":          (lambda: get_copy_comida("merienda"),     "/nutricion/formulario/"),
        "cena":              (lambda: get_copy_comida("cena"),         "/nutricion/formulario/"),
        "agua":              (get_copy_hidratacion,                    "/"),
        "actividad":         (lambda: get_copy_actividad(kwargs.get("nombre_actividad", "")), "/calendario/"),
        "seguimiento":       (get_copy_registro_progreso,              "/seguimiento/tablero/"),
        "registro":          (get_copy_registro_comida,                "/nutricion/formulario/"),
        "receta":            (lambda: get_copy_receta(kwargs.get("nombre_receta", "")), "/recetas/"),
        "motivacion":        (get_copy_motivacion,                     "/seguimiento/tablero/"),
        "resumen":           (get_copy_resumen,                        "/seguimiento/tablero/"),
        "medicion_hoy":      (get_copy_medicion_hoy,                   "/seguimiento/tablero/"),
        "medicion_proxima":  (get_copy_medicion_proxima,               "/seguimiento/tablero/"),
        "motivacion_progreso": (
            lambda: get_copy_motivacion_progreso(
                kwargs.get("progreso", 0), kwargs.get("dias", 0)
            ),
            "/seguimiento/tablero/",
        ),
    }

    if categoria not in CATEGORIAS:
        return {"error": f"Categoría '{categoria}' no existe. Opciones: {list(CATEGORIAS.keys())}"}

    get_copy_fn, link = CATEGORIAS[categoria]
    titulo, mensaje = get_copy_fn()

    return enviar_notificacion_a_usuario(
        usuario_id=usuario_id,
        titulo=titulo,
        mensaje=mensaje,
        data={"tipo": categoria},
        link=link,
    )