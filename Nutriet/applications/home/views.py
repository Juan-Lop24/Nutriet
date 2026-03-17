from django.shortcuts import render
import requests
from django.conf import settings
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from Nutriet.utils import verificar_formulario_completo

from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.shortcuts import redirect

from applications.seguimiento.models import MedicionFisica
from applications.Apispoonacular.models import RecetaFavorita
from applications.nutricion.models import FormularioNutricionGuardado
from applications.seguimiento.engine import analizar
import json

@never_cache
@login_required
@verificar_formulario_completo
def main(request):

    # =====================
    # 🔥 MENSAJE BIENVENIDA
    # =====================
    show_welcome = request.session.pop('show_welcome', False)

    # =====================
    # RECETAS FAVORITAS
    # =====================
    favoritas = RecetaFavorita.objects.filter(
        usuario=request.user
    ).order_by('-id')[:3]

    # =====================
    # MEDICIONES + ANÁLISIS
    # =====================
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
            print("Error en analisis main:", e)

    # =====================
    # PROGRESO
    # =====================
    if analisis:
        progreso         = analisis['progress']['progreso_porcentaje']
        dias_registrados = mediciones.count()
        objetivo_dias    = None
    else:
        dias_registrados = mediciones.count()
        objetivo_dias    = 30
        progreso = min(int((dias_registrados / objetivo_dias) * 100), 100)

    # =====================
    # GRÁFICAS
    # =====================
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

    # =====================
    # RECETAS RANDOM
    # =====================
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
        print("Error trayendo recetas random:", e)

    context = {
        'show_welcome': show_welcome,
        'notificaciones_configuradas': request.user.notificaciones_configuradas,
        'dias_registrados': dias_registrados,
        'objetivo_dias': objetivo_dias,
        'progreso': progreso,
        'fechas_peso': json.dumps(fechas_peso),
        'pesos': json.dumps(pesos),
        'fechas_grasa': json.dumps(fechas_grasa),
        'grasas': json.dumps(grasas),
        'favoritas': favoritas,
        'recetas_random': recetas_random,
    }
    show_welcome = request.session.pop('show_welcome', False)
    print("SHOW_WELCOME:", show_welcome)

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

from django.core.mail import send_mail
from django.http import JsonResponse

def contacto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email_usuario = request.POST.get('email')
        asunto_seleccionado = request.POST.get('asunto')
        mensaje = request.POST.get('mensaje')

        cuerpo = f"Has recibido un nuevo mensaje de: {nombre}\n"
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
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    return render(request, 'contactos.html')

class informacionviews(TemplateView):
    template_name = 'informacion.html'


# ── Health Check ──────────────────────────────────────────────────────────────
from django.db import connection
from django.utils import timezone

def health_check(request):
    """
    Endpoint de health check para Render / Railway / uptime monitors.
    Verifica: DB, Firebase, Scheduler.
    """
    status = {"status": "ok", "timestamp": timezone.now().isoformat(), "checks": {}}
    http_status = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
        http_status = 503

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
