from django.conf import settings


def onesignal_config(request):
    """
    Expone el App ID de OneSignal a todos los templates.
    Reemplaza el anterior firebase_config.
    """
    return {
        'ONESIGNAL_APP_ID': getattr(settings, 'ONESIGNAL_APP_ID', ''),
    }
