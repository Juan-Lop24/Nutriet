# applications/notificacion/apps.py
import os
from django.apps import AppConfig


class NotificacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications.notificacion'
    verbose_name = 'Notificaciones'

    def ready(self):
        """
        Se ejecuta cuando Django termina de cargar.
        Arranca el scheduler de notificaciones automáticamente.

        En modo DEBUG con reloader, Django lanza dos procesos.
        RUN_MAIN='true' identifica el proceso hijo (el real).
        En producción (sin reloader), RUN_MAIN no está seteado,
        así que arrancamos siempre salvo que sea el proceso padre del reloader.
        """
        import sys
        # En 'runserver' con reloader, saltamos el proceso padre (evita doble inicio)
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from .scheduler import iniciar_scheduler
            iniciar_scheduler()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"No se pudo iniciar el scheduler de notificaciones: {e}"
            )
