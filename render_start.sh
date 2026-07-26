#!/bin/bash

echo "🚀 Iniciando deploy no Render..."

# 🔥 VAI DIRETAMENTE PARA A PASTA DA API USANDO CAMINHO ABSOLUTO
cd /opt/render/project/src/apps/api

# 🔥 FORÇA O USO DO settings_prod.py
export DJANGO_SETTINGS_MODULE=settings_prod

# Coletar arquivos estáticos
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Aplicar migrações
echo "🗄️ Aplicando migrações..."
python manage.py migrate --noinput

# 🔥 INICIAR O SERVIDOR (SEM --settings)
echo "🔥 Iniciando servidor..."
gunicorn config.wsgi:application --bind 0.0.0.0:10000