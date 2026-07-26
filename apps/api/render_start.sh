#!/bin/bash

echo "🚀 Iniciando deploy no Render..."

# Coletar arquivos estáticos com o caminho correto
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Aplicar migrações
echo "🗄️ Aplicando migrações..."
python manage.py migrate --noinput

# Iniciar o servidor
echo "🔥 Iniciando servidor..."
gunicorn config.wsgi:application