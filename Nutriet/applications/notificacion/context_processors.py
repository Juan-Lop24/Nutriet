from django.conf import settings
import json


def firebase_config(request):
    """Expone la configuración web de Firebase para las plantillas."""
    config = getattr(settings, 'FIREBASE_WEB_CONFIG', {})
    vapid = getattr(settings, 'FIREBASE_VAPID_KEY', '')

    return {
        'FIREBASE_WEB_CONFIG': json.dumps(config),
        'FIREBASE_VAPID_KEY': vapid,
    }
