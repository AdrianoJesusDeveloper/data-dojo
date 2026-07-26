#!/bin/bash

echo "🚀 Iniciando deploy no Render..."

export DJANGO_SETTINGS_MODULE=settings_prod

echo "🗄 Aplicando migrações..."
python manage.py migrate --noinput

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🔥 Iniciando servidor..."

exec gunicorn apps.api.wsgi:application --bind 0.0.0.0:$PORT