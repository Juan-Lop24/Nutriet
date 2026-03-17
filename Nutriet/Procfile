# ══════════════════════════════════════════════════════════════
#  NutriET — Procfile (Railway / Heroku / Render)
# ══════════════════════════════════════════════════════════════

# Servidor web principal
web: gunicorn -c gunicorn.conf.py Nutriet.wsgi:application

# Worker de Celery (descomentar si tienes Redis configurado)
# worker: celery -A Nutriet worker --loglevel=info --concurrency=2

# Beat de Celery para tareas periódicas (alternativa a APScheduler con Redis)
# beat: celery -A Nutriet beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
