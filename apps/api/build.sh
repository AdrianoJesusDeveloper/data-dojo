
#!/bin/bash

echo "🚀 Build iniciado..."

pip install -r requirements.txt

echo "📦 Coletando arquivos estáticos..."

python manage.py collectstatic --noinput

echo "✅ Build concluído!"
