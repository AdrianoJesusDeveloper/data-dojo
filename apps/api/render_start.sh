#!/bin/bash

# Aplicar migrações
python manage.py migrate

# Coletar arquivos estáticos
python manage.py collectstatic --noinput

# Executar o servidor com Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT