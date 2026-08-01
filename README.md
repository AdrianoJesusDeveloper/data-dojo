# Data Driven Dojô ⚔️📊

Uma plataforma gamificada para formação de profissionais de dados, construída com React, TypeScript, Vite e Django REST.

## Visão Geral

O Data Driven Dojô combina gamificação, trilhas de aprendizado e um workspace interativo para acelerar a jornada de profissionais de dados. O sistema atual permite cadastrar cursos, módulos, aulas, vídeos e exercícios, além de oferecer um ambiente de desafio com editor SQL e feedback visual.

## Tecnologias

- Frontend: React + TypeScript + Vite
- Roteamento: TanStack Router
- Estado e dados: TanStack React Query
- Estilização: Tailwind CSS
- Notificações: Sonner
- Gráficos: Recharts
- Backend: Django 6 + Django REST Framework
- Autenticação: dj-rest-auth + token auth
- Data store: PostgreSQL (opcional SQLite em dev)
- Filas: Celery + Redis

## Estrutura do Repositório

- [src](src) — frontend React
  - [src/routes](src/routes) — páginas do app
  - [src/components](src/components) — componentes reutilizáveis
  - [src/lib](src/lib) — estado do Dojô e helpers
- [apps/api](apps/api) — backend Django
  - [apps/api/core](apps/api/core) — modelos, serializers, views e rotas
  - [apps/api/config](apps/api/config) — configuração do Django
- [apps/api/requirements.txt](apps/api/requirements.txt) — dependências Python
- [package.json](package.json) — dependências e scripts do frontend

## Funcionalidades Principais

- Cadastro e login de usuários
- Dashboard de progresso com gráficos de XP, horas e streak
- Workspace de desafio com editor SQL simulado
- Feed de comunidade com posts, curtidas e comentários falsos
- Persistência local do estado do usuário no navegador
- Integração com backend Django para cursos, módulos, aulas, vídeos e exercícios
- Suporte a exercícios estruturados com enunciado, tipo, resposta esperada e critérios de avaliação

## Arquitetura e Diagramas

A documentação abaixo descreve a arquitetura atual do sistema com foco em estrutura, fluxo de dados, comportamento e modelagem.

### 1. Diagrama estrutural / arquitetura de alto nível

```mermaid
flowchart LR
    Usuario[Usuário] --> Frontend[Frontend React + Vite]
    Frontend --> API[Django REST API]
    API --> BD[(Banco de Dados)]
    API --> Media[Arquivos de mídia]
    API --> Redis[(Redis)]
    API --> Celery[Workers Celery]
```

### 2. Diagrama de componentes

```mermaid
flowchart TB
    subgraph Frontend
        Router[Router TanStack]
        Pages[Páginas do workspace e autenticação]
        Store[Store do Dojô]
        UI[Componentes UI]
    end

    subgraph Backend
        Views[Views/API]
        Models[Models Django]
        Serializers[Serializers DRF]
        Admin[Admin Django]
    end

    Router --> Pages
    Pages --> Store
    Pages --> UI
    Pages --> Views
    Views --> Serializers
    Views --> Models
    Admin --> Models
```

### 3. Diagrama de pacotes

```mermaid
flowchart TB
    subgraph src
        routes[Routes]
        components[Components]
        lib[Lib]
    end

    subgraph apps.api
        core[Core App]
        config[Config App]
    end

    core --> config
    routes --> components
    routes --> lib
```

### 4. Diagrama de classes

```mermaid
classDiagram
    class User {
        +id
        +email
        +username
        +first_name
        +last_name
    }

    class Course {
        +id
        +title
        +description
        +created_at
    }

    class Module {
        +id
        +title
        +order
    }

    class Lesson {
        +id
        +title
        +content_type
        +file_upload
        +video_url
        +body
        +order
    }

    class Exercise {
        +id
        +title
        +statement
        +answer_type
        +expected_answer
        +expected_keywords
        +evaluation_mode
        +points
        +evaluate_answer(answer)
    }

    Course "1" --> "0..*" Module : possui
    Module "1" --> "0..*" Lesson : contém
    Lesson "1" --> "0..1" Exercise : possui
```

### 5. Diagrama de implantação

```mermaid
flowchart TB
    Browser[Browser / Mobile] --> Vite[Vite Dev Server]
    Vite --> Frontend[Frontend React]
    Frontend --> API[API Django REST]
    API --> Postgres[(PostgreSQL)]
    API --> Redis[(Redis)]
    API --> Media[(Arquivos de mídia)]
    Celery[Celery Worker] --> Redis
    Celery --> Postgres
```

### 6. Diagrama de objetos

```mermaid
flowchart LR
    curso1[Curso: SQL para Dados]
    modulo1[Módulo: Fundamentos]
    aula1[Aula: Introdução ao SELECT]
    aula2[Aula: Exercício SQL]

    curso1 --> modulo1
    modulo1 --> aula1
    modulo1 --> aula2
```

### 7. Diagrama de casos de uso

```mermaid
flowchart TD
    Usuario[Aluno] --> UC1[Entrar no sistema]
    Usuario --> UC2[Visualizar cursos]
    Usuario --> UC3[Assistir aula]
    Usuario --> UC4[Enviar resposta do desafio]
    Usuario --> UC5[Visualizar progresso]
```

### 8. Diagrama de sequência

```mermaid
sequenceDiagram
    participant Aluno as Aluno
    participant Front as Frontend
    participant API as Django API
    participant DB as Banco

    Aluno->>Front: Acessa workspace
    Front->>API: GET /api/courses/
    API->>DB: Busca cursos, módulos e aulas
    DB-->>API: Dados retornados
    API-->>Front: JSON com conteúdo
    Front-->>Aluno: Renderiza vídeo, aulas e editor
```

### 9. Diagrama de atividades

```mermaid
flowchart TD
    A[Aluno abre o workspace] --> B[Frontend carrega curso]
    B --> C[API retorna módulos e aulas]
    C --> D[Usuário escolhe uma aula]
    D --> E[Exibe vídeo ou texto do exercício]
    E --> F[Usuário envia solução]
    F --> G[Sistema valida resposta]
    G --> H[Exibe feedback e XP]
```

### 10. Diagrama de máquina de estados

```mermaid
stateDiagram-v2
    [*] --> Carregando
    Carregando --> Pronto: dados carregados
    Carregando --> Erro: falha de conexão
    Pronto --> Assistindo: selecionar aula
    Assistindo --> Respondendo: abrir desafio
    Respondendo --> Validando: submeter resposta
    Validando --> Pronto: resposta aceita
    Validando --> Respondendo: resposta reprovada
    Erro --> [*]
```

### 11. Diagrama de entidade-relacionamento (DER)

```mermaid
erDiagram
    USER ||--o{ COURSE : cria
    COURSE ||--o{ MODULE : possui
    MODULE ||--o{ LESSON : contém
    LESSON ||--o| EXERCISE : possui

    USER {
        int id
        string email
        string username
    }

    COURSE {
        int id
        string title
        string description
        datetime created_at
    }

    MODULE {
        int id
        int course_id
        string title
        int order
    }

    LESSON {
        int id
        int module_id
        string title
        string content_type
        string file_upload
        string video_url
        text body
        int order
    }

    EXERCISE {
        int id
        int lesson_id
        string title
        text statement
        string answer_type
        text expected_answer
        json expected_keywords
        string evaluation_mode
        int points
    }
```

### 12. Diagrama de fluxo de dados (DFD)

```mermaid
flowchart LR
    Usuario[Aluno] -->|envia ação| Frontend[Frontend]
    Frontend -->|requisição| API[API Django]
    API -->|consulta| DB[(Banco de Dados)]
    API -->|serve mídia| Storage[Arquivos de mídia]
    API -->|retorna dados| Frontend
    Frontend -->|apresenta feedback| Usuario
```

### 13. Visão de fluxo de conteúdo do curso

```mermaid
flowchart TD
    Curso[Curso] --> Modulo1[Módulo 1]
    Curso --> Modulo2[Módulo 2]
    Modulo1 --> Aula1[Aula de vídeo]
    Modulo1 --> Aula2[Exercício]
    Modulo2 --> Aula3[Aula de apostila]
    Modulo2 --> Aula4[Laboratório]
```

## Correções Aplicadas

- Corrigido toggle de curtidas em [src/routes/community.tsx](src/routes/community.tsx), garantindo atualização correta de estado e contagem.
- Ajustado `beforeLoad` em [src/routes/index.tsx](src/routes/index.tsx) para evitar acesso a `localStorage` durante SSR.
- Adicionado `TokenAuthentication` nas configurações do Django para compatibilidade com `dj-rest-auth`.
- Permitido CORS para `http://localhost:5173` e `http://127.0.0.1:5173` no backend.

## Configuração Local

### Frontend

1. Instale dependências:
   ```bash
    npm install
   ```
2. Inicie o frontend:
   ```bash
   npm run dev
   ```
3. Abra em `http://localhost:5173`

### Backend

1. Acesse o backend:
   ```bash
   cd apps/api
   ```
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute migrações:
   ```bash
   python manage.py migrate
   ```
5. Inicie o servidor:
   ```bash
   python manage.py runserver
   ```

### Banco de Dados

- O backend usa PostgreSQL por padrão com configuração em [apps/api/config/settings.py](apps/api/config/settings.py).
- Para usar SQLite local, defina `DJANGO_USE_SQLITE=True` nas variáveis de ambiente.

## Endpoints Principais

- `GET /api/courses/`
- `GET /api/modules/`
- `GET /api/lessons/`
- `POST /api/auth/login/`
- `POST /api/auth/registration/`

## Scripts Úteis

- `npm run dev` — iniciar frontend em desenvolvimento
- `npm run build` — gerar build de produção
- `npm run preview` — visualizar build
- `npm run lint` — executar ESLint

## Uso

1. Inicie o backend Django.
2. Inicie o frontend Vite.
3. Acesse `http://localhost:5173`.

## Observações

- O workspace carrega o primeiro curso disponível e usa validação simples de SQL para aprovação de desafios.
- O feed comunitário é alimentado por posts seed e permite curtidas locais.
- A autenticação é baseada em token gravado no `localStorage`.
- A autenticação é baseada em token gravado no `localStorage`.

---

**.gitignore — documentação e boas práticas**

Objetivo

- Fornecer orientação clara sobre o propósito de `/.gitignore` e as categorias de arquivos que não devem ser versionadas.

Por que manter um `.gitignore` bem escrito

- Protege segredos e credenciais (ex.: arquivos `.env`).
- Evita incluir dependências e artefatos binários que incham o repositório.
- Reduz o risco de conflitos e commits acidentais de arquivos gerados localmente.

Categorias recomendadas

- Dependências e builds: `node_modules/`, `.output/`, `dist/`, `build/`
- Ambientes e caches: `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`
- Dados locais e uploads: `db.sqlite3`, `media/`, `uploads/`
- Arquivos sensíveis: `.env`, `.env.local`, `credentials.json`
- Ferramentas/IDE: `.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db`
- Logs e relatórios: `npm-debug.log`, `yarn-debug.log`, `coverage/`

Trecho de exemplo (recomenda-se revisar para o seu contexto)

```
# Node / frontend
node_modules/
.output/

# Python / Django
.venv/
venv/
db.sqlite3
media/

# Ambiente local / Segredos
.env

# IDEs / OS
.vscode/
.DS_Store
```

Como remover um arquivo já comitado por engano

1. Remova do índice, mantendo-o no disco:

   git rm --cached path/to/file
2. Commit e push:

   git commit -m "chore: remover arquivo sensível do repositório"
   git push

Manutenção

- Atualize o arquivo quando adicionar novas ferramentas/fluxos de build.
- Use templates oficiais do GitHub como base: https://github.com/github/gitignore
