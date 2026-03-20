from django.shortcuts import redirect
from django.urls import reverse

# Rutas que NO deben ser interceptadas (accesibles sin verificar código)
RUTAS_LIBRES = [
    '/usuarios/verificacion-login/',
    '/usuarios/reenviar-codigo/',
    '/usuarios/login/',
    '/usuarios/register/',
    '/usuarios/logout/',
    '/usuarios/recover/',
    '/usuarios/verificar/',
    '/usuarios/cambiar/',
    '/google/',          # callback de Google OAuth
    '/admin/',
    '/static/',
    '/media/',
]


class VerificacionCodigoMiddleware:
    """
    Si el usuario está autenticado pero todavía no verificó su código 2FA,
    lo redirige a la pantalla de verificación sin importar desde qué URL llegue.
    Esto corrige el bug donde cambiar a 'sitio de escritorio' en móvil
    saltaba la verificación.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar si la ruta actual es libre
            ruta = request.path_info
            es_libre = any(ruta.startswith(r) for r in RUTAS_LIBRES)

            if not es_libre:
                from .models import VerificacionCodigo
                verificacion = VerificacionCodigo.objects.filter(
                    usuario=request.user
                ).first()

                # Si existe verificación pendiente (no verificada y no expirada), forzar
                if verificacion and not verificacion.verificado:
                    if not verificacion.esta_expirado():
                        return redirect('/usuarios/verificacion-login/')
                    # Si expiró, limpiarla para no bloquear al usuario para siempre
                    else:
                        verificacion.verificado = True
                        verificacion.save()

        return self.get_response(request)