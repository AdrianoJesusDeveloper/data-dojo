#!/bin/bash

echo "🚀 Iniciando deploy no Render..."

# 🔥 ADICIONA O DIRETÓRIO APPS AO PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/opt/render/project/src/apps"

# 🔥 FORÇA O SETTINGS_PROD
export DJANGO_SETTINGS_MODULE=api.settings_prod

# Entrar na pasta do Django
cd apps/api

# Coletar estáticos
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --settings=settings_prod

# Migrações
echo "🗄️ Aplicando migrações..."
python manage.py migrate --noinput --settings=settings_prod

# Iniciar servidor
echo "🔥 Iniciando servidor..."
gunicorn config.wsgi:application --bind 0.0.0.0:10000