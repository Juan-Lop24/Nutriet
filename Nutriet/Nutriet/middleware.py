"""
Nutriet/middleware.py
=====================
Middleware de seguridad que fuerza los headers HTTP en CADA respuesta.

Por qué existe este archivo:
  Django tiene configuraciones como X_FRAME_OPTIONS y SECURE_HSTS_SECONDS,
  pero en Render con WhiteNoise a veces esos headers no llegan al navegador
  porque el middleware de Django los aplica solo en ciertas condiciones
  (ej: SecurityMiddleware solo aplica HSTS en respuestas HTTPS confirmadas).
  Este middleware los fuerza directamente en el objeto response, sin condiciones.

Cómo usarlo:
  En prod.py, agregar al INICIO de MIDDLEWARE:
    'Nutriet.middleware.SecurityHeadersMiddleware'
"""


class SecurityHeadersMiddleware:
    """
    Agrega headers de seguridad HTTP a todas las respuestas.
    Debe ser el PRIMER middleware en la lista para que siempre se ejecute.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # ✅ Previene Clickjacking — el sitio no puede ser embebido en un iframe
        response["X-Frame-Options"] = "DENY"

        # ✅ Previene MIME sniffing — el navegador respeta el Content-Type declarado
        response["X-Content-Type-Options"] = "nosniff"

        # ✅ Protección XSS en navegadores antiguos
        response["X-XSS-Protection"] = "1; mode=block"

        # ✅ HSTS — el navegador recuerda que este dominio SOLO acepta HTTPS
        # max-age=31536000 = 1 año | includeSubDomains | preload
        response["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # ✅ Referrer Policy — no enviar la URL completa a sitios externos
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ✅ Permissions Policy — desactivar APIs del navegador que no usamos
        response["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
        )

        return response