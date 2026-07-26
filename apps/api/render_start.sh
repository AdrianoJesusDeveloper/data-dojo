#!/bin/bash

echo "🚀 Iniciando deploy no Render..."

# Entrar na pasta do Django
cd apps/api

# Coletar estáticos
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --settings=settings_prod

# Migrações
echo "🗄️ Aplicando migrações..."
python manage.py migrate --noinput --settings=settings_prod

# 🔥 VARIÁVEIS DE AMBIENTE PARA FORÇAR WHITENOISE
export WHITENOISE_USE_FINDERS=1
export WHITENOISE_MANIFEST_STRICT=0
export WHITENOISE_AUTOREFRESH=1

# 🔥 INICIAR SERVIDOR COM CONFIGURAÇÃO EXPLÍCITA
echo "🔥 Iniciando servidor..."
gunicorn config.wsgi:application \
    --settings=settings_prod \
    --env WHITENOISE_USE_FINDERS=1 \
    --env WHITENOISE_MANIFEST_STRICT=0 \
    --bind 0.0.0.0:10000