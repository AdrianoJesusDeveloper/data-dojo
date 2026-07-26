import os
from django.core.wsgi import get_wsgi_application

# 🔥 FORÇAR O SETTINGS_PROD
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings_prod')

application = get_wsgi_application()
