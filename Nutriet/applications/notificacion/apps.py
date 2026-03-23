from django.apps import AppConfig


class NotificacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications.notificacion'
    verbose_name = 'Notificaciones'

    def ready(self):
        """Inicia el scheduler de notificaciones programadas."""
        import os
        # En modo DEBUG con autoreload, Django lanza dos procesos.
        # RUN_MAIN='true' solo está presente en el proceso principal (no en el watcher).
        # Sin DEBUG (producción), RUN_MAIN no existe, por eso se permite también ese caso.
        run_main = os.environ.get('RUN_MAIN')
        is_main_process = run_main == 'true' or run_main is None
        if is_main_process:
            try:
                from .scheduler import iniciar_scheduler
                iniciar_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "No se pudo iniciar el scheduler: %s", e
                )