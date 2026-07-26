# apps/api/build.sh
#!/bin/bash

echo "🚀 Iniciando build do Data Driven Dojô Backend..."

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Coletar arquivos estáticos
echo "📁 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Executar migrações
echo "🗄️  Executando migrações..."
python manage.py migrate --noinput

echo "✅ Build concluído com sucesso!"