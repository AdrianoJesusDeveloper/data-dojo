#!/bin/bash

echo "🚀 Build iniciado..."

# Instalar dependências
pip install -r requirements.txt

# Criar diretório para estáticos
mkdir -p staticfiles

# Coletar estáticos
echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Verificar se os arquivos foram copiados
echo "📁 Arquivos em staticfiles:"
ls -la staticfiles/

echo "✅ Build concluído!"