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

## Agentes de IA

Os agentes são habilitados somente no ambiente local por padrão. O Docker
Compose define `AI_ENABLED=true`; os serviços do Render definem
`AI_ENABLED=false`. Chaves de provedores devem permanecer apenas em arquivos
locais ignorados pelo Git e nunca devem ser incluídas na imagem Docker.

Para habilitar IA futuramente em produção:

1. Configure `AI_ENABLED=true` no serviço web e no worker.
2. Cadastre pelo menos um secret de provedor, como `GEMINI_API_KEY` ou
   `OPENAI_API_KEY`, nos dois serviços.
3. Defina `AI_DEFAULT_PROVIDER` com o provedor principal (`gemini` ou
   `openai`). Opcionalmente, configure `AI_FALLBACK_PROVIDERS`.
4. Faça um novo deploy e confirme `available: true` em
   `/api/ai/agents/`. Valide uma conversa sem registrar chaves ou respostas
   sensíveis nos logs.

Enquanto `AI_ENABLED=false`, a listagem apresenta os agentes como
indisponíveis e o endpoint de conversa responde HTTP 503.
