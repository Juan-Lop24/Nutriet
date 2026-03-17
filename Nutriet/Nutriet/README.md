# 🥗 NutriET — Guía de Despliegue en Producción

NutriET es una aplicación web Django de seguimiento nutricional con IA, notificaciones push Firebase, autenticación Google y recomendaciones personalizadas.

---

## 📋 Requisitos

| Componente | Mínimo | Recomendado |
|---|---|---|
| Python | 3.11+ | 3.11+ |
| RAM | 512 MB | 1 GB |
| Disco | 2 GB | 5 GB |
| Base de datos | SQLite | PostgreSQL 15+ |
| Caché/Cola | — | Redis 7+ |

---

## ⚡ Deploy Rápido (Railway / Render / Heroku)

### 1. Variables de entorno

Copia `.env.example` a `.env` y rellena:

```bash
cp .env.example .env
```

Las variables **obligatorias** son:

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta Django (generar con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `ALLOWED_HOSTS` | Tu dominio, ej: `nutriet.com,www.nutriet.com` |
| `GOOGLE_CLIENT_ID` | OAuth de Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth de Google Cloud Console |
| `FIREBASE_VAPID_KEY` | Firebase Console → Project Settings → Cloud Messaging |
| `GEMINI_API_KEY` | Google AI Studio |
| `EMAIL_HOST_PASSWORD` | Contraseña de aplicación Gmail |

Las variables **opcionales pero recomendadas**:

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | PostgreSQL: `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis: `redis://host:6379/0` |
| `SECURE_SSL_REDIRECT` | `True` en producción con HTTPS |

### 2. Ejecutar deploy

```bash
bash deploy.sh --prod
```

### 3. Iniciar servidor

```bash
# Producción
gunicorn -c gunicorn.conf.py Nutriet.wsgi:application

# Desarrollo
python manage.py runserver
```

---

## 🚂 Railway

1. Conecta tu repositorio en [railway.app](https://railway.app)
2. Añade un servicio **PostgreSQL** y uno **Redis** desde el dashboard
3. En tu servicio web, agrega las variables de entorno del `.env.example`
4. Railway detecta `railway.toml` automáticamente

---

## 🎨 Render

1. Sube tu código a GitHub
2. En [render.com](https://render.com) → New → Blueprint
3. Render detecta `render.yaml` y crea la app + DB + Redis automáticamente
4. Agrega las variables secretas en el panel de Render

---

## 🐳 Docker

```bash
# Construir imagen
docker build -t nutriet .

# Desarrollo completo (app + DB + Redis + Nginx)
docker-compose up --build

# Solo la app (si ya tienes DB y Redis externos)
docker run -p 8000:8000 --env-file .env nutriet
```

---

## 🖥️ VPS / Servidor Dedicado (Ubuntu/Debian)

### Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/tu-usuario/nutriet.git /var/www/nutriet
cd /var/www/nutriet

# 2. Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables
cp .env.example .env
nano .env   # Editar con tus valores reales

# 5. Preparar la app
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 6. Configurar Nginx
sudo cp nginx.conf /etc/nginx/sites-available/nutriet
sudo ln -s /etc/nginx/sites-available/nutriet /etc/nginx/sites-enabled/
# Editar las rutas en nginx.conf para tu servidor
sudo nginx -t && sudo systemctl reload nginx

# 7. Configurar systemd
sudo cp nutriet.service /etc/systemd/system/
# Editar las rutas en nutriet.service
sudo systemctl daemon-reload
sudo systemctl enable nutriet
sudo systemctl start nutriet

# 8. SSL con Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tudominio.com -d www.tudominio.com
```

### Comandos útiles

```bash
# Ver logs en vivo
sudo journalctl -u nutriet -f

# Reiniciar la app
sudo systemctl restart nutriet

# Estado
sudo systemctl status nutriet
```

---

## 🔥 Firebase (Notificaciones Push)

Las notificaciones push requieren configuración en Firebase Console:

1. Ve a [Firebase Console](https://console.firebase.google.com)
2. Proyecto `sanguine-robot-478914-g6`
3. **Project Settings → Cloud Messaging** → copia la VAPID Key a `FIREBASE_VAPID_KEY`
4. **Project Settings → Service Accounts** → genera una clave privada → guarda como `serviceAccountKey.json` en la raíz del proyecto
5. En **Authentication → Authorized domains** agrega tu dominio de producción
6. En **Google Cloud Console → APIs & OAuth** agrega tu dominio a los orígenes y callbacks de OAuth

> ⚠️ **Importante:** El archivo `serviceAccountKey.json` contiene credenciales privadas. Nunca lo subas a Git. Súbelo directamente a tu servidor o úsalo como variable de entorno (base64).

---

## 🤖 Scheduler de Notificaciones

El scheduler APScheduler se inicia automáticamente con Django. No requiere configuración adicional.

Las tareas programadas son:

| Hora | Tarea |
|---|---|
| 07:30 | Recordatorio desayuno |
| 09:00, 15:00 | Recordatorio hidratación |
| 10:00 | Recordatorio media mañana |
| 12:30 | Recordatorio almuerzo |
| 15:30 | Recordatorio merienda |
| 19:00 | Recordatorio cena |
| Cada 15 min | Notificaciones de calendario en tiempo real |
| 20:30 | Recordatorio si no registró comida |
| 21:00 | Resumen diario |
| Lun/Mié/Vie 09:00 | Motivación con datos de progreso |
| Mar/Jue 11:00 | Receta personalizada |
| Lunes 08:00 | Resumen semanal |

Verifica que el scheduler está activo en: `GET /health/`

---

## 🏥 Health Check

```
GET /health/
```

Respuesta exitosa:
```json
{
  "status": "ok",
  "timestamp": "2025-03-04T10:00:00",
  "checks": {
    "database": "ok",
    "firebase": "ok",
    "scheduler": "running",
    "scheduler_jobs": 17
  }
}
```

---

## 📁 Estructura del Proyecto

```
nutriet/
├── applications/
│   ├── ai/              # Cálculos nutricionales (IMC, TMB, TDEE)
│   ├── Apispoonacular/  # Integración API Spoonacular
│   ├── base/            # Modelos base
│   ├── calendario/      # Calendario de actividades
│   ├── home/            # Landing page + health check
│   ├── notificacion/    # Sistema de notificaciones push FCM
│   ├── nutricion/       # Formularios y planes nutricionales con IA
│   ├── recetas/         # Catálogo MealDB + clasificación Gemini
│   ├── seguimiento/     # Mediciones físicas y tablero
│   └── Usuarios/        # Auth, perfiles, Google OAuth
├── Nutriet/
│   ├── settings.py      # Configuración principal
│   └── setting/
│       ├── base.py
│       ├── local.py
│       └── prod.py      # Configuración de producción
├── .env                 # Variables de entorno (NO subir a Git)
├── .env.example         # Plantilla de variables
├── deploy.sh            # Script de deploy
├── docker-compose.yml   # Stack completo con Docker
├── Dockerfile
├── gunicorn.conf.py     # Config Gunicorn
├── nginx.conf           # Config Nginx
├── nutriet.service      # Servicio systemd
├── Procfile             # Railway / Heroku
├── railway.toml         # Config Railway
├── render.yaml          # Config Render
└── requirements.txt
```

---

## 🔒 Seguridad en Producción

- [x] `DEBUG = False`
- [x] `SECRET_KEY` desde variable de entorno
- [x] HTTPS enforced (HSTS, SSL redirect)
- [x] Cookies seguras (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- [x] Headers de seguridad (`X-Frame-Options`, `X-Content-Type-Options`)
- [x] WhiteNoise con archivos comprimidos y fingerprinting
- [x] Logs rotativos (no llenan el disco)
- [x] `serviceAccountKey.json` fuera del repositorio

---

*NutriET — Aplicación de nutrición inteligente*
