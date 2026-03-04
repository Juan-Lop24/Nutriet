"""
Configuración de Gunicorn para producción — NutriET
"""
import multiprocessing
import os

# ── Workers ───────────────────────────────────────────────────────────────────
# Fórmula recomendada: (2 × núcleos) + 1
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"   # 'sync' es estable; usa 'gevent' si tienes muchas conexiones I/O
threads = int(os.getenv("GUNICORN_THREADS", 2))
worker_connections = 1000
max_requests = 1200          # Reiniciar worker después de N requests (evita memory leaks)
max_requests_jitter = 100    # Jitter para evitar que todos reinicien a la vez

# ── Binding ───────────────────────────────────────────────────────────────────
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout = 120           # 2 min — suficiente para llamadas a IA (Gemini / OpenAI)
graceful_timeout = 30
keepalive = 5

# ── Logging ───────────────────────────────────────────────────────────────────
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = "-"     # stdout
errorlog = "-"      # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ── App ───────────────────────────────────────────────────────────────────────
wsgi_app = "Nutriet.wsgi:application"

# ── Misc ──────────────────────────────────────────────────────────────────────
preload_app = True      # Carga la app antes de hacer fork (ahorra RAM con copy-on-write)
forwarded_allow_ips = "*"   # Confiar en X-Forwarded-For de cualquier proxy
proxy_protocol = False
