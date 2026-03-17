from django.apps import AppConfig


class NotificacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications.notificacion'
    verbose_name = 'Notificaciones'

    def ready(self):
        """Inicia el scheduler de notificaciones programadas."""
        import os
        # Solo arrancar en el proceso principal (no en el worker de autoreload)
        if os.environ.get('RUN_MAIN') != 'true' and os.environ.get('DJANGO_SETTINGS_MODULE'):
            try:
                from .scheduler import iniciar_scheduler
                iniciar_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "No se pudo iniciar el scheduler: %s", e
                )
