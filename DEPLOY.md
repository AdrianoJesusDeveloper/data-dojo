# Guia de Deploy Gratuito — Data Driven Dojô

Deploy completo em 4 plataformas gratuitas: Vercel (frontend), Railway (backend), Supabase (banco) e Groq (IA).

---

## Visão Geral

```
Usuário → Vercel (Frontend React)
              ↓
         Railway (Django API)
              ↓          ↓
        Supabase      Groq AI
       (PostgreSQL)  (LLM grátis)
```

---

## PASSO 1 — Groq (IA gratuita) — 3 minutos

1. Acesse **https://console.groq.com**
2. Clique em **"Sign Up"** → entre com Google
3. No menu lateral, clique em **"API Keys"**
4. Clique em **"Create API Key"**
5. Dê o nome: `data-dojo-prod`
6. **Copie a chave** — começa com `gsk_...`
7. Guarde em um bloco de notas: `GROQ_API_KEY=gsk_...`

---

## PASSO 2 — Supabase (banco de dados) — 5 minutos

1. Acesse **https://supabase.com**
2. Clique em **"Start your project"** → entre com GitHub
3. Clique em **"New project"**
4. Preencha:
   - **Name:** `data-dojo`
   - **Database Password:** crie uma senha forte (guarde!)
   - **Region:** `South America (São Paulo)`
5. Aguarde ~2 minutos para criar
6. No menu lateral, clique em **"Project Settings"** → **"Database"**
7. Role até **"Connection string"** → selecione a aba **"URI"**
8. Copie a string — parece com: `postgresql://postgres:[SUA-SENHA]@...supabase.co:5432/postgres`
9. **Substitua `[YOUR-PASSWORD]` pela senha que você criou**
10. Guarde: `DATABASE_URL=postgresql://postgres:...`

---

## PASSO 3 — Railway (backend Django) — 10 minutos

1. Acesse **https://railway.app**
2. Clique em **"Login"** → entre com GitHub
3. Clique em **"New Project"** → **"Deploy from GitHub repo"**
4. Selecione o repositório `data-dojo`
5. Railway vai detectar o projeto — clique em **"Add service"**
6. Clique no serviço criado → aba **"Settings"**
7. Em **"Root Directory"**, coloque: `apps/api`
8. Em **"Start Command"**, coloque:
   ```
   python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
   ```
9. Vá para a aba **"Variables"** e adicione **todas** estas variáveis:

```
DJANGO_SETTINGS_MODULE=config.settings_prod
SECRET_KEY=<gere em https://djecrety.ir>
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=<seu-app>.up.railway.app,<seu-dominio.com>
DATABASE_URL=<cole o DATABASE_URL do Supabase>
REDIS_URL=<deixe em branco por enquanto>
AI_ENABLED=True
GROQ_API_KEY=<cole sua chave do Groq>
GROQ_MODEL=openai/gpt-oss-20b
AI_DEFAULT_PROVIDER=groq
AI_FALLBACK_PROVIDERS=groq,gemini
CORS_ALLOWED_ORIGINS=https://<seu-dominio.com>,https://<seu-app>.vercel.app
CSRF_TRUSTED_ORIGINS=https://<seu-dominio.com>,https://<seu-app>.vercel.app
PAYMENT_BACKEND=sandbox
ACCOUNT_EMAIL_VERIFICATION=none
DDJ_CONTENT_STUDIO_ENABLED=False
```

10. Vá para aba **"Deployments"** e aguarde o deploy ficar verde ✅
11. Na aba **"Settings"** → **"Networking"** → copie a URL pública
    - Parece com: `https://data-dojo-api-production.up.railway.app`
12. Guarde: `VITE_API_URL=https://data-dojo-api-production.up.railway.app`

---

## PASSO 4 — Vercel (frontend) — 5 minutos

1. Acesse **https://vercel.com**
2. Clique em **"Sign Up"** → entre com GitHub
3. Clique em **"Add New Project"**
4. Selecione o repositório `data-dojo`
5. Em **"Framework Preset"** → selecione **Vite**
6. Em **"Root Directory"** → deixe como `/` (raiz)
7. Clique em **"Environment Variables"** e adicione:

```
VITE_API_URL=<URL do Railway do passo 3>
```

8. Clique em **"Deploy"** e aguarde ✅
9. Depois que deployar, vá em **"Settings"** → **"Domains"**
10. Clique em **"Add"** e digite seu domínio
11. Siga as instruções para adicionar os registros DNS no seu provedor de domínio:
    - Adicione um registro **CNAME** apontando para `cname.vercel-dns.com`
    - Ou registros **A** apontando para os IPs que a Vercel mostrar

---

## PASSO 5 — Atualizar CORS no Railway

Depois que o Vercel atribuir o domínio, volte ao Railway e atualize as variáveis:

```
CORS_ALLOWED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com
CSRF_TRUSTED_ORIGINS=https://seu-dominio.com,https://www.seu-dominio.com
```

---

## Criar o primeiro usuário admin

Após o deploy, crie o superusuário via Railway:

1. No Railway, clique no serviço → aba **"Settings"** → **"Shell"**
2. Execute:
```bash
python manage.py createsuperuser
```
3. Preencha email, username e senha

---

## Verificação final

| Teste | URL esperada |
|---|---|
| API respondendo | `https://sua-api.up.railway.app/health/` → `{"status": "ok"}` |
| Frontend carregando | `https://seu-dominio.com` |
| Login funcionando | `https://seu-dominio.com/login` |
| IA respondendo | Ir em `/ai-sales` e mandar uma mensagem |

---

## Custos

| Plataforma | Plano | Custo |
|---|---|---|
| Vercel | Hobby | **Gratuito** |
| Railway | Trial ($5/mês de crédito) | **Gratuito** para uso leve |
| Supabase | Free tier (500MB) | **Gratuito** |
| Groq | Free tier | **Gratuito** |

> **Nota:** O Railway dá $5 de crédito mensal. Uma API Django leve consome ~$2-3/mês, então é suficiente para uso pessoal/demonstração.

---

## Problemas comuns

**Deploy falha no Railway:**
- Verifique se `Root Directory` está como `apps/api`
- Verifique se `DJANGO_SETTINGS_MODULE=config.settings_prod` está definido

**CORS error no frontend:**
- Certifique que `CORS_ALLOWED_ORIGINS` inclui a URL exata do Vercel (com `https://`)

**IA não responde:**
- Verifique se `AI_ENABLED=True` e `GROQ_API_KEY` está correto
- Teste a chave em https://console.groq.com/playground
