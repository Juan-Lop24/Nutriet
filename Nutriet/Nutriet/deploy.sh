#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  NutriET — Script de deploy automático
#  Uso: bash deploy.sh [--prod]
#  Con --prod: usa settings de producción
# ══════════════════════════════════════════════════════════════════════════════

set -e   # Salir si cualquier comando falla

SETTINGS="Nutriet.settings"
if [[ "$1" == "--prod" ]]; then
    SETTINGS="Nutriet.setting.prod"
    echo "🚀 Desplegando en modo PRODUCCIÓN..."
else
    echo "🛠  Desplegando en modo DESARROLLO..."
fi

export DJANGO_SETTINGS_MODULE="$SETTINGS"

echo ""
echo "📦 [1/7] Instalando dependencias..."
pip install -r requirements.txt --quiet

echo ""
echo "🗄  [2/7] Aplicando migraciones..."
python manage.py migrate --noinput

echo ""
echo "📂 [3/7] Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

echo ""
echo "🔄 [4/7] Creando directorio de logs..."
mkdir -p logs

echo ""
echo "🔥 [5/7] Verificando configuración Firebase..."
if [ -f "serviceAccountKey.json" ]; then
    echo "   ✅ serviceAccountKey.json encontrado"
else
    echo "   ⚠️  ADVERTENCIA: serviceAccountKey.json NO encontrado"
    echo "      Las notificaciones push NO funcionarán sin este archivo."
    echo "      Descárgalo desde Firebase Console → Configuración del proyecto → Cuentas de servicio"
fi

echo ""
echo "🔑 [6/7] Verificando variables de entorno críticas..."
python - << 'PYEOF'
import os
from dotenv import load_dotenv
load_dotenv()

required = [
    "SECRET_KEY",
    "GEMINI_API_KEY",
    "FIREBASE_VAPID_KEY",
    "EMAIL_HOST_PASSWORD",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f"   ⚠️  Variables faltantes en .env: {', '.join(missing)}")
    print("      Copia .env.example a .env y rellena los valores.")
else:
    print("   ✅ Todas las variables críticas están configuradas")
PYEOF

echo ""
echo "✅ [7/7] Deploy completado"
echo ""
echo "▶  Para iniciar el servidor:"
echo "   Desarrollo:  python manage.py runserver"
echo "   Producción:  gunicorn -c gunicorn.conf.py Nutriet.wsgi:application"
echo ""

echo ""
echo "👤 Creando superusuario si no existe..."
python - << 'PYEOF'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Nutriet.settings")
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
email    = os.getenv("SUPERUSER_EMAIL")
password = os.getenv("SUPERUSER_PASSWORD")
username = os.getenv("SUPERUSER_USERNAME", "admin")
if email and password:
    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print("   Superusuario creado: " + username)
    else:
        print("   El superusuario ya existe")
else:
    print("   SUPERUSER_EMAIL o SUPERUSER_PASSWORD no definidos, se omite")
PYEOF