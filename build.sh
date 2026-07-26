#!/bin/bash

echo "🚀 Build iniciado..."

# Instalar dependências
pip install -r requirements.txt

# Coletar estáticos
python manage.py collectstatic --noinput

echo "✅ Build concluído!"