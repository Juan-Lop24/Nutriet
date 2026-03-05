# applications/notificacion/scheduler.py
"""
Configura APScheduler para ejecutar las tareas de notificaciones.

Este módulo es llamado desde NotificacionConfig.ready() en apps.py,
lo que hace que el scheduler arranque automáticamente con Django.

Horarios (Colombia UTC-5):
  07:30  Desayuno
  10:00  Media mañana
  12:30  Almuerzo
  15:30  Merienda
  19:00  Cena
  09:00, 15:00  Hidratación (2 veces al día — no saturar)
  08:00          Actividades del calendario (resumen matutino)
  */15           Notificaciones de calendario en tiempo real (15 min antes del evento)
  00:05          Reset flags de calendario
  08:00          Recordatorio de medición física (solo si toca ese día o el siguiente)
  11:00 mar,jue  Receta personalizada según perfil del usuario
  09:00 lun,mié,vie  Motivación con datos reales de progreso
  08:00 lunes    Seguimiento semanal
  20:30          Recordatorio de registro si no registró comida
  21:00          Resumen diario
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings

logger = logging.getLogger(__name__)

# Instancia global del scheduler
_scheduler = None


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=getattr(settings, 'TIME_ZONE', 'America/Bogota'))
    return _scheduler


def iniciar_scheduler():
    """
    Registra todas las tareas y arranca el scheduler.
    Solo se ejecuta una vez (protegido contra doble inicio en modo DEBUG con reloader).
    """
    from .tasks import (
        tarea_recordatorio_desayuno,
        tarea_recordatorio_media_manana,
        tarea_recordatorio_almuerzo,
        tarea_recordatorio_merienda,
        tarea_recordatorio_cena,
        tarea_recordatorio_agua,
        tarea_recordatorio_actividades_calendario,
        tarea_recordatorio_registro_progreso,
        tarea_recordatorio_registro_comida,
        tarea_nueva_receta,
        tarea_motivacion,
        tarea_resumen_diario,
        # Nuevas tareas
        tarea_recordatorio_medicion,
        tarea_receta_personalizada,
        tarea_motivacion_con_progreso,
        tarea_notificaciones_calendario_tiempo_real,
        tarea_reset_notificaciones_calendario,
    )

    scheduler = get_scheduler()

    if scheduler.running:
        logger.info("Scheduler ya está corriendo, saltando inicio.")
        return

    # ── CAT 1: Comidas (horarios estrictos según formulario del usuario) ──────
    scheduler.add_job(
        tarea_recordatorio_desayuno,
        CronTrigger(hour=7, minute=30),
        id="recordatorio_desayuno",
        replace_existing=True,
    )
    scheduler.add_job(
        tarea_recordatorio_media_manana,
        CronTrigger(hour=10, minute=0),
        id="recordatorio_media_manana",
        replace_existing=True,
    )
    scheduler.add_job(
        tarea_recordatorio_almuerzo,
        CronTrigger(hour=12, minute=30),
        id="recordatorio_almuerzo",
        replace_existing=True,
    )
    scheduler.add_job(
        tarea_recordatorio_merienda,
        CronTrigger(hour=15, minute=30),
        id="recordatorio_merienda",
        replace_existing=True,
    )
    scheduler.add_job(
        tarea_recordatorio_cena,
        CronTrigger(hour=19, minute=0),
        id="recordatorio_cena",
        replace_existing=True,
    )

    # ── CAT 2: Hidratación (2 veces al día: mañana y tarde) ──────────────────
    # Máximo 2 para no saturar. Uno a las 9am, otro a las 3pm.
    scheduler.add_job(
        tarea_recordatorio_agua,
        CronTrigger(hour=9, minute=0),
        id="agua_manana",
        replace_existing=True,
    )
    scheduler.add_job(
        tarea_recordatorio_agua,
        CronTrigger(hour=15, minute=0),
        id="agua_tarde",
        replace_existing=True,
    )

    # ── CAT 3: Calendario – tiempo real (cada 15 min) ─────────────────────────
    scheduler.add_job(
        tarea_notificaciones_calendario_tiempo_real,
        CronTrigger(minute='*/15'),           # cada 15 minutos
        id="calendario_tiempo_real",
        replace_existing=True,
    )
    # Reset flags diario a las 00:05
    scheduler.add_job(
        tarea_reset_notificaciones_calendario,
        CronTrigger(hour=0, minute=5),
        id="reset_calendario_flags",
        replace_existing=True,
    )
    # Resumen general de actividades del día (mantener también el daily)
    scheduler.add_job(
        tarea_recordatorio_actividades_calendario,
        CronTrigger(hour=8, minute=0),        # resumen matutino
        id="actividades_calendario_resumen",
        replace_existing=True,
    )

    # ── CAT 4: Medición física (chequeo diario a las 8am) ────────────────────
    # Notificará solo a quienes les toque ese día o el día siguiente
    scheduler.add_job(
        tarea_recordatorio_medicion,
        CronTrigger(hour=8, minute=0),
        id="recordatorio_medicion",
        replace_existing=True,
    )

    # ── CAT 5: Recetas personalizadas (martes y jueves) ───────────────────────
    scheduler.add_job(
        tarea_receta_personalizada,
        CronTrigger(day_of_week="tue,thu", hour=11, minute=0),
        id="receta_personalizada",
        replace_existing=True,
    )

    # ── CAT 6: Motivación con datos reales (lun, mié, vie) ────────────────────
    scheduler.add_job(
        tarea_motivacion_con_progreso,
        CronTrigger(day_of_week="mon,wed,fri", hour=9, minute=0),
        id="motivacion_progreso",
        replace_existing=True,
    )

    # ── CAT 7: Seguimiento semanal (lunes 8am) ────────────────────────────────
    scheduler.add_job(
        tarea_recordatorio_registro_progreso,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="seguimiento_semanal",
        replace_existing=True,
    )

    # ── CAT 8: Recordatorio de registro si no ha comido (8:30pm) ─────────────
    scheduler.add_job(
        tarea_recordatorio_registro_comida,
        CronTrigger(hour=20, minute=30),
        id="recordatorio_registro",
        replace_existing=True,
    )

    # ── CAT 9: Resumen diario (9pm) ───────────────────────────────────────────
    scheduler.add_job(
        tarea_resumen_diario,
        CronTrigger(hour=21, minute=0),
        id="resumen_diario",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✅ NutriET Scheduler iniciado con %d tareas", len(scheduler.get_jobs()))


def detener_scheduler():
    """Detiene el scheduler limpiamente (para tests o shutdown)."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido.")


def listar_tareas() -> list[dict]:
    """Retorna información de todas las tareas programadas."""
    scheduler = get_scheduler()
    if not scheduler.running:
        return []
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "nombre": job.name,
            "proximo_disparo": str(job.next_run_time),
        })
    return jobs