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

# Iniciar servidor (ficando dentro da pasta api)
echo "🔥 Iniciando servidor..."
gunicorn config.wsgi:application --settings=settings_prod

# Voltar para a raiz (não necessário, mas mantido)
cd ../..