FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY apps/api/ /app/
COPY apps/api/config /app/config

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings_prod

# Script de inicialização
COPY apps/api/render_start.sh .
RUN chmod +x render_start.sh

EXPOSE 8000

CMD ["./render_start.sh"]