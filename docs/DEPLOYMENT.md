# 🚀 Deployment — Data Driven Dojô

## Arquitetura de produção proposta

```text
                    Internet
                       │
              ┌────────┴────────┐
              │                 │
           Vercel             Render
         Frontend             Backend
              │                 │
              │          ┌──────┼─────────┐
              │          │      │         │
              │       Django  Celery    Health
              │          │      │
              │       PostgreSQL  Key Value
              │
              └────── HTTPS / API ────────┘
```

## Frontend — Vercel

O repositório já contém `vercel.json` com build Vite e fallback de SPA.

Variável necessária:

```text
VITE_API_URL=https://SEU-BACKEND.onrender.com
```

Depois do primeiro deploy do backend, substitua a URL no projeto Vercel e faça um novo deploy.

## Backend — Render

O repositório contém `render.yaml` com:

- Django API em Docker;
- health check `/health/`;
- PostgreSQL gerenciado;
- Key Value compatível com Redis;
- worker Celery;
- migrations antes do deploy.

As variáveis `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS` devem receber a URL HTTPS do frontend.

## Docker local

```bash
docker compose up --build
```

Serviços:

```text
Frontend: http://localhost:8080
API:      http://localhost:8000
Health:   http://localhost:8000/health/
Postgres: localhost:5432
Redis:    localhost:6379
```

## Checklist pós-deploy

- [ ] frontend abre em HTTPS;
- [ ] `/health/` retorna `status=ok`;
- [ ] migrations concluídas;
- [ ] login funciona;
- [ ] frontend consegue chamar a API;
- [ ] CORS está restrito ao domínio do frontend;
- [ ] Celery está conectado ao Key Value;
- [ ] PostgreSQL está acessível apenas pelos serviços necessários;
- [ ] não existem secrets no repositório;
- [ ] CI está verde.

## Limitação do plano gratuito

O ambiente gratuito do Render é adequado para demonstração e testes, mas possui limitações de disponibilidade e persistência. Para produção real, use planos com persistência, backups e recursos de operação adequados.
