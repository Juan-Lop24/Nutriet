from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views import View
from django.db import connection
from django.utils import timezone


class MainViews(View):
    """Vista principal de la landing page."""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('cuestionario')
        return render(request, 'index.html')


def health_check(request):
    """
    Endpoint de health check para balanceadores de carga, uptime monitors y Railway/Render.
    Verifica: DB, Firebase disponible, scheduler corriendo.
    """
    status = {"status": "ok", "timestamp": timezone.now().isoformat(), "checks": {}}
    http_status = 200

    # ── Check base de datos ────────────────────────────────────────────────────
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
        http_status = 503

    # ── Check Firebase Admin SDK ───────────────────────────────────────────────
    try:
        import firebase_admin
        status["checks"]["firebase"] = "ok" if firebase_admin._apps else "not_initialized"
    except Exception as e:
        status["checks"]["firebase"] = f"error: {str(e)}"

    # ── Check Scheduler ────────────────────────────────────────────────────────
    try:
        from applications.notificacion.scheduler import get_scheduler
        sch = get_scheduler()
        status["checks"]["scheduler"] = "running" if sch.running else "stopped"
        if sch.running:
            status["checks"]["scheduler_jobs"] = len(sch.get_jobs())
    except Exception as e:
        status["checks"]["scheduler"] = f"error: {str(e)}"

    return JsonResponse(status, status=http_status)
