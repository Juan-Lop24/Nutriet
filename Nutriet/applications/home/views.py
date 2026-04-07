from django.shortcuts import render
from django.conf import settings
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.core.mail import send_mail
from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
from django.core.cache import cache

from Nutriet.utils import verificar_formulario_completo
from applications.seguimiento.models import MedicionFisica
from applications.Apispoonacular.models import RecetaFavorita
from applications.nutricion.models import FormularioNutricionGuardado
from applications.seguimiento.engine import analizar
import json
import logging
import re

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_ip(request):
    """IP real del cliente detrás del proxy de Render."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _rate_limited(key, max_requests, period_seconds):
    """
    Devuelve True si se superó el límite (bloquear).
    Devuelve False si está dentro del límite (permitir).
    Usa el cache de Django — Redis en producción, memoria local en dev.
    """
    current = cache.get(key, 0)
    if current >= max_requests:
        return True
    cache.set(key, current + 1, timeout=period_seconds)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

@never_cache
@login_required
@verificar_formulario_completo
def main(request):
    show_welcome = request.session.pop('show_welcome', False)

    mostrar_advertencia = request.session.pop('mostrar_advertencia', False)
    
    favoritas = RecetaFavorita.objects.filter(
        usuario=request.user
    ).order_by('-id')[:3]

    formulario = FormularioNutricionGuardado.objects.filter(
        usuario=request.user
    ).last()

    mediciones = MedicionFisica.objects.filter(
        usuario=request.user
    ).order_by('fecha')

    analisis      = None
    analisis_json = '{}'

    if formulario and mediciones.exists():
        try:
            analisis      = analizar(formulario, mediciones)
            analisis_json = json.dumps(analisis)
        except Exception as e:
            logger.warning(f"Error en análisis main user={request.user.pk}: {e}")

    if analisis:
        progreso         = analisis['progress']['progreso_porcentaje']
        dias_registrados = mediciones.count()
        objetivo_dias    = None
    else:
        dias_registrados = mediciones.count()
        objetivo_dias    = 30
        progreso = min(int((dias_registrados / objetivo_dias) * 100), 100)

    if analisis:
        charts = analisis.get('charts', {})

        def _series(key):
            fechas, vals = [], []
            for pt in charts.get(key, []):
                if pt.get('value') is not None:
                    fechas.append(pt['date'])
                    vals.append(pt['value'])
            return fechas, vals

        fechas_peso,  pesos  = _series('weight_over_time')
        fechas_grasa, grasas = _series('bodyfat_over_time')
    else:
        fechas_peso, pesos, fechas_grasa, grasas = [], [], [], []
        for m in mediciones:
            if m.peso:
                fechas_peso.append(m.fecha.strftime('%d %b'))
                pesos.append(float(m.peso))
            if m.grasa_corporal:
                fechas_grasa.append(m.fecha.strftime('%d %b'))
                grasas.append(float(m.grasa_corporal))

    recetas_random = []
    try:
        from applications.recetas.models import RecetaMealDB
        import random as _random
        qs_ids = list(
            RecetaMealDB.objects.filter(
                clasificado=True, imagen_url__isnull=False
            ).exclude(imagen_url="").values_list("id", flat=True)
        )
        if qs_ids:
            muestra_ids = _random.sample(qs_ids, min(3, len(qs_ids)))
            for r in RecetaMealDB.objects.filter(id__in=muestra_ids):
                recetas_random.append({
                    "id":     r.id,
                    "titulo": r.nombre_es or r.nombre,
                    "imagen": r.imagen_url,
                })
    except Exception as e:
        logger.warning(f"Error trayendo recetas random: {e}")

    context = {
        'show_welcome':                show_welcome,
        'mostrar_advertencia':         mostrar_advertencia,
        'notificaciones_configuradas': request.user.notificaciones_configuradas,
        'dias_registrados':            dias_registrados,
        'objetivo_dias':               objetivo_dias,
        'progreso':                    progreso,
        'fechas_peso':                 json.dumps(fechas_peso),
        'pesos':                       json.dumps(pesos),
        'fechas_grasa':                json.dumps(fechas_grasa),
        'grasas':                      json.dumps(grasas),
        'favoritas':                   favoritas,
        'recetas_random':              recetas_random,
    }

    return render(request, 'main.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(verificar_formulario_completo, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class MainViews(TemplateView):
    template_name = 'main.html'


class indexviews(TemplateView):
    template_name = 'index.html'


class socialviews(TemplateView):
    template_name = 'redes_sociales.html'


class informacionviews(TemplateView):
    template_name = 'informacion.html'


# ─────────────────────────────────────────────────────────────────────────────
# CONTACTO  ✅ FIX: rate limit + validación de inputs
# ─────────────────────────────────────────────────────────────────────────────

def contacto(request):
    if request.method == 'POST':
        ip = _get_ip(request)

        # ✅ FIX CRÍTICO: rate limit — máx 5 mensajes por IP por hora
        # Evita que un bot envíe miles de correos a atencionclientenutriet@gmail.com
        rl_key = f"contacto_rl:{ip}"
        if _rate_limited(rl_key, max_requests=5, period_seconds=3600):
            logger.warning(f"Rate limit contacto superado — IP: {ip}")
            return JsonResponse(
                {'ok': False, 'error': 'Demasiados mensajes. Intenta de nuevo en una hora.'},
                status=429
            )

        # ✅ FIX: extraer y sanitizar todos los campos
        nombre              = request.POST.get('nombre', '').strip()[:100]
        email_usuario       = request.POST.get('email', '').strip()[:200]
        asunto_seleccionado = request.POST.get('asunto', '').strip()[:100]
        mensaje             = request.POST.get('mensaje', '').strip()[:2000]

        # ✅ FIX: validar que los campos requeridos no estén vacíos
        if not nombre or not email_usuario or not asunto_seleccionado or not mensaje:
            return JsonResponse(
                {'ok': False, 'error': 'Todos los campos son obligatorios.'},
                status=400
            )

        # ✅ FIX: validar formato de email básico
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_usuario):
            return JsonResponse(
                {'ok': False, 'error': 'El correo electrónico no es válido.'},
                status=400
            )

        # ✅ FIX: whitelist de asuntos válidos
        ASUNTOS_VALIDOS = {
            'Consulta general', 'Información de pedido',
            'Soporte técnico', 'Sugerencia', 'Reclamo', 'Otro'
        }
        if asunto_seleccionado not in ASUNTOS_VALIDOS:
            asunto_seleccionado = 'Consulta general'

        cuerpo  = f"Has recibido un nuevo mensaje de: {nombre}\n"
        cuerpo += f"Correo del cliente: {email_usuario}\n"
        cuerpo += f"Asunto: {asunto_seleccionado}\n\n"
        cuerpo += f"Mensaje:\n{mensaje}"

        try:
            send_mail(
                subject=f"WEB NUTRIET: {asunto_seleccionado}",
                message=cuerpo,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=['atencionclientenutriet@gmail.com'],
                fail_silently=False,
            )
            return JsonResponse({'ok': True})
        except Exception as e:
            logger.error(f"Error enviando correo de contacto: {e}")
            return JsonResponse({'ok': False, 'error': 'Error al enviar el mensaje.'}, status=500)

    return render(request, 'contactos.html')


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

def health_check(request):
    """Endpoint de health check para Render / uptime monitors."""
    status     = {"status": "ok", "timestamp": timezone.now().isoformat(), "checks": {}}
    http_status = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"]             = "degraded"
        http_status                  = 503

    try:
        import firebase_admin
        status["checks"]["firebase"] = "ok" if firebase_admin._apps else "not_initialized"
    except Exception as e:
        status["checks"]["firebase"] = f"error: {str(e)}"

    try:
        from applications.notificacion.scheduler import get_scheduler
        sch = get_scheduler()
        status["checks"]["scheduler"] = "running" if sch.running else "stopped"
        if sch.running:
            status["checks"]["scheduler_jobs"] = len(sch.get_jobs())
    except Exception as e:
        status["checks"]["scheduler"] = f"error: {str(e)}"

    return JsonResponse(status, status=http_status)