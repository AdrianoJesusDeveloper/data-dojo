#!/bin/bash

echo "🚀 Build iniciado..."

# Instalar dependências
pip install -r requirements.txt

# Entrar na pasta do Django
cd apps/api

# Coletar estáticos (usando settings_prod diretamente, sem "api.")
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --settings=settings_prod

# Voltar para a raiz
cd ../..

echo "✅ Build concluído!"