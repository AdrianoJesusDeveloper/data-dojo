# Manual do ecossistema 3DS em ambiente local

Este manual mostra como executar e testar localmente o Data Driven Dojô, a API Django, a 3DStore e o Dojo Command Center. Para administrar produtos, consulte também o [Manual da 3DStore](manual_3DStore_produtos.md).

## 1. Arquitetura local

```mermaid
flowchart LR
    U[Navegador] -->|8083| F[Frontend React/TanStack]
    F -->|HTTP 8000| A[API Django]
    A -->|5432| P[(PostgreSQL)]
    A -->|6379| R[(Redis)]
    W[Celery Worker] --> R
    W --> P
    U -->|8501| S[Dojo Command Center]
    S --> P
```

| Componente | URL/porta local |
|---|---|
| Data Driven Dojô | `http://127.0.0.1:8083/` |
| 3DStore | `http://127.0.0.1:8083/store` |
| API Django | `http://127.0.0.1:8000/` |
| Health check | `http://127.0.0.1:8000/health/` |
| Django Admin | `http://127.0.0.1:8000/admin/` |
| Dojo Command Center | `http://127.0.0.1:8501/` |
| PostgreSQL | `127.0.0.1:5432` |
| Redis | `127.0.0.1:6379` |

## 2. Pré-requisitos

- Git
- Node.js 22 ou superior
- Python 3.11 a 3.13
- Docker Desktop com Docker Compose
- Aproximadamente 5 GB livres

No PowerShell, confira:

```powershell
git --version
node --version
python --version
docker --version
docker compose version
```

Se o PowerShell bloquear `npm.ps1`, utilize `npm.cmd` nos comandos deste manual.

## 3. Preparar o projeto

Abra o PowerShell na raiz do repositório:

```powershell
Set-Location "C:\projetos\DATA-DRIVEN-DOJÔ-3DS\plataform-3DS\Nova pasta\data-dojo"
git status
```

Não coloque senhas reais em arquivos versionados. `.env`, `.env.local` e ambientes virtuais já são ignorados pelo Git.

## 4. Criar o ambiente Python

Na raiz:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r apps\api\requirements.txt
pip install -r analytics\requirements.txt
```

Se o ambiente apontar para uma versão antiga/removida do Python, renomeie a pasta `.venv`, instale uma versão suportada e crie o ambiente novamente.

## 5. Subir PostgreSQL e Redis

O modo recomendado usa Docker somente para os serviços de infraestrutura:

```powershell
docker compose up -d db redis
docker compose ps
```

Credenciais locais padrão:

```text
Banco: dojo_db
Usuário: dojo
Senha: dojo_dev_password
Host: localhost
Porta: 5432
```

Esses valores são apenas para desenvolvimento local.

Para parar sem apagar os dados:

```powershell
docker compose stop db redis
```

`docker compose down -v` apaga os volumes e todos os dados locais. Não execute sem ter certeza.

## 6. Configurar a API Django

Crie `apps/api/.env` com:

```dotenv
SECRET_KEY=chave-local-longa-e-nao-usada-em-producao
DEBUG=True
ENVIRONMENT=development
DATABASE_URL=postgresql://dojo:dojo_dev_password@127.0.0.1:5432/dojo_db
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://127.0.0.1:8083,http://localhost:8083
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8083,http://localhost:8083
FRONTEND_URL=http://127.0.0.1:8083
```

Chaves de IA e e-mail são opcionais. Cadastre-as somente se for testar essas integrações.

### Preparar o banco

Com o ambiente Python ativo:

```powershell
Set-Location apps\api
python manage.py check
python manage.py migrate
python manage.py createsuperuser
Set-Location ..\..
```

As migrações também inserem os produtos fictícios previstos pelo projeto.

### Executar a API

Em um terminal próprio:

```powershell
Set-Location "C:\projetos\DATA-DRIVEN-DOJÔ-3DS\plataform-3DS\Nova pasta\data-dojo"
.\.venv\Scripts\Activate.ps1
Set-Location apps\api
python manage.py runserver 127.0.0.1:8000
```

Teste em outro terminal:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/
```

## 7. Configurar e executar o frontend

Crie `.env.local` na raiz:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_DOJO_DASHBOARD_URL=http://127.0.0.1:8501/
```

Abra outro terminal na raiz:

```powershell
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1 --port 8083
```

Acesse `http://127.0.0.1:8083/`. Mantenha o terminal do Vite aberto.

```text
FRONTEND
├─ /                  página inicial
├─ /register          criar conta
├─ /login             entrar
├─ /dashboard         painel do aluno
├─ /workspace         formações e aulas
├─ /community         comunidade
├─ /portfolio         portfólios
├─ /store             3DStore
└─ /ai                IA Sensei
```

## 8. Executar o Dojo Command Center

O dashboard usa a mesma `DATABASE_URL` configurada em `apps/api/.env`.

Em outro terminal, na raiz:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DOJO_ADMIN_PASSWORD="senha-admin-somente-local"
$env:DASHBOARD_REFRESH_SECONDS="60"
$env:DOJO_APP_URL="http://127.0.0.1:8083/"
$env:LEXDATA_URL="https://lexdata-frontend.vercel.app/"
$env:MARKETING_URL="https://lexdata-frontend.vercel.app/#agencia-3ds"
streamlit run analytics\app.py --server.port 8501
```

Acesse `http://127.0.0.1:8501/`. Em **Visão geral**, valide usuários, cursos, produtos, pedidos, receita, cancelamentos e gráficos. A seção **Administração** pede a senha definida em `DOJO_ADMIN_PASSWORD`.

## 9. Executar o Celery (opcional)

O worker é necessário somente para tarefas assíncronas. No Windows, use o pool `solo`:

```powershell
Set-Location apps\api
..\..\.venv\Scripts\Activate.ps1
celery -A config worker --loglevel=INFO --pool=solo
```

## 10. Ordem correta de inicialização

```mermaid
sequenceDiagram
    participant D as Docker
    participant B as Django
    participant F as Frontend
    participant S as Streamlit
    D->>D: PostgreSQL + Redis
    B->>D: migrate e conectar
    B->>B: runserver :8000
    F->>B: consumir API
    F->>F: Vite :8083
    S->>D: consultar PostgreSQL
    S->>S: Streamlit :8501
```

1. Docker Desktop.
2. PostgreSQL e Redis.
3. Migrações e API Django.
4. Frontend.
5. Streamlit.
6. Celery, quando necessário.

## 11. Roteiro de teste funcional

1. Abra `/register` e crie um usuário.
2. Entre em `/login`.
3. Confira dashboard, perfil e workspace.
4. Publique um projeto no portfólio.
5. Crie um tópico na comunidade.
6. Abra `/store`, pesquise e filtre produtos.
7. Selecione quantidade e adicione ao carrinho.
8. Remova um item e confirme que desaparece.
9. Finalize e depois cancele um pedido pendente.
10. Confirme que o pedido cancelado não aparece na vitrine.
11. Abra o Command Center e confira o cancelamento no indicador de churn.
12. Entre no Django Admin e teste imagem e vídeo seguindo o manual da 3DStore.

## 12. Testes automatizados

### Frontend

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test -- --run
npm.cmd run build
```

Avisos do ESLint não interrompem o processo; erros precisam ser corrigidos.

### Backend

Com PostgreSQL ativo:

```powershell
Set-Location apps\api
..\..\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test core.tests store.tests --verbosity=2
```

### Analytics

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s analytics\tests -p "test_*.py"
```

## 13. Encerrar o ambiente

Nos terminais do Django, Vite, Streamlit e Celery, pressione `Ctrl + C`. Depois:

```powershell
docker compose stop db redis
```

Os dados permanecem nos volumes Docker para a próxima execução.

## 14. Solução de problemas

### Frontend abre, mas o catálogo retorna erro 500

- Confirme que Django e PostgreSQL estão ativos.
- Execute `python manage.py migrate`.
- Confira `VITE_API_URL=http://127.0.0.1:8000`.
- Veja o erro no terminal do Django.

### CORS ou CSRF

Use o mesmo host nas URLs. Se abrir o frontend em `127.0.0.1:8083`, inclua exatamente essa origem em `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS`.

### Hydration failed

- Pare o Vite e inicie novamente.
- Teste em janela anônima sem extensões que alterem o HTML.
- Confirme que não existem dois servidores frontend em portas diferentes.
- Execute novamente `npm.cmd install` se as dependências mudaram.

### Porta ocupada

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -In 8000,8083,8501,5432,6379
```

Encerre o processo correto ou escolha outra porta e atualize as variáveis relacionadas.

### Python aponta para instalação inexistente

Recrie `.venv` usando um Python 3.11–3.13 funcional. Um ambiente virtual não deve ser copiado entre máquinas ou sobreviver à remoção do Python que o criou.

### Streamlit sem gráficos

- Confirme `DATABASE_URL` em uma única linha.
- Em ambiente local, use host `127.0.0.1`; dentro do Docker, use host `db`.
- Teste o PostgreSQL e reinicie o Streamlit.
- Ative temporariamente `$env:DASHBOARD_DEBUG="true"` para visualizar o tipo do erro, sem expor Secrets.

### Imagens enviadas não aparecem

Com `DEBUG=True`, o Django serve `/media/` localmente. Em produção, use uma URL pública em storage persistente.

## 15. Regras de segurança

- Nunca publique `.env` ou screenshots com senhas.
- Use credenciais diferentes entre local e produção.
- Não use a External Database URL do Render no ambiente local sem necessidade.
- Não execute migrações destrutivas sem backup.
- Antes de qualquer deploy, execute testes, build e confira `git status`.

