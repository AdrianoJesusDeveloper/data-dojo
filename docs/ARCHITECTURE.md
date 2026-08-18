# 🏗️ Data Driven Dojô — Arquitetura e Diagramas

> Documento técnico complementar ao README. Mantém os diagramas originais do projeto e adiciona a arquitetura-alvo da evolução do Dojô.

---

## 1. Arquitetura-alvo — visão estratégica

A nova arquitetura mantém a separação entre experiência, aplicação, dados e processamento assíncrono, preparando o Dojô para crescer sem perder simplicidade.

```mermaid
flowchart TB
    User[👤 Aluno / Sensei] --> Web[🌐 Web App\nReact + TypeScript + Vite]
    Web --> Router[🧭 TanStack Router]
    Web --> Query[⚡ TanStack Query]
    Router --> UI[🎨 UI / Design System]
    Query --> API[🔐 Django REST API]

    API --> Auth[🔑 Auth / Permissions]
    API --> Learning[🎓 Learning Domain]
    API --> Gamification[🥋 Gamification Domain]
    API --> Community[👥 Community Domain]
    API --> Portfolio[💼 Portfolio Domain]
    API --> AI[🤖 AI Sensei Layer]

    Learning --> DB[(🐘 PostgreSQL)]
    Gamification --> DB
    Community --> DB
    Portfolio --> DB
    Auth --> DB

    API --> Cache[(⚡ Redis)]
    API --> Queue[📨 Task Queue]
    Queue --> Celery[⚙️ Celery Workers]
    Celery --> DB
    Celery --> Storage[(🗂️ Media / Object Storage)]

    AI --> Providers[AI Providers]
    AI --> Knowledge[(📚 Dojô Knowledge / RAG)]

    API --> Observability[📈 Logs / Metrics / Traces]
    Web --> Observability
```

### Camadas da arquitetura-alvo

| Camada | Responsabilidade | Tecnologias principais |
|---|---|---|
| Experience | Interface, navegação e UX | React, TypeScript, Vite |
| Routing & Data | Rotas, cache e sincronização | TanStack Router, TanStack Query |
| Application | Regras e APIs | Django, DRF |
| Domains | Aprendizagem, gamificação, comunidade, portfólio | Django Apps |
| AI | Mentoria, feedback e personalização | AI providers + RAG |
| Data | Persistência transacional | PostgreSQL |
| Cache/Queue | Performance e tarefas assíncronas | Redis + Celery |
| Storage | Vídeos, arquivos e mídia | Object Storage |
| Observability | Saúde técnica e produto | Logs, métricas e traces |

---

## 2. Arquitetura de domínio

A evolução deve separar o backend por **domínios de negócio**, evitando concentrar toda a lógica em uma única aplicação Django.

```mermaid
flowchart LR
    Core[Core / Identity]
    Learning[Learning]
    Gamification[Gamification]
    Community[Community]
    Portfolio[Portfolio]
    AI[AI Sensei]
    Analytics[Analytics]

    Core --> Learning
    Core --> Community
    Core --> Portfolio
    Learning --> Gamification
    Learning --> Analytics
    Gamification --> Analytics
    Community --> Analytics
    Portfolio --> Analytics
    AI --> Learning
    AI --> Gamification
```

### Responsabilidades

- **Identity/Core:** usuário, autenticação, permissões e perfil-base.
- **Learning:** cursos, trilhas, módulos, aulas e exercícios.
- **Gamification:** XP, faixas, badges, streak e conquistas.
- **Community:** posts, comentários, curtidas e interação.
- **Portfolio:** projetos, evidências e apresentação profissional.
- **AI Sensei:** recomendações, feedback e mentoria contextual.
- **Analytics:** eventos de aprendizagem e indicadores de produto.

---

## 3. Fluxo principal do aluno

```mermaid
sequenceDiagram
    participant A as Aluno
    participant W as Web App
    participant API as Django API
    participant DB as PostgreSQL
    participant Q as Redis/Celery
    participant AI as IA Sensei

    A->>W: Abre trilha / aula
    W->>API: Solicita conteúdo
    API->>DB: Consulta progresso e conteúdo
    DB-->>API: Dados
    API-->>W: Conteúdo + progresso
    W-->>A: Renderiza experiência

    A->>W: Envia desafio
    W->>API: POST resposta
    API->>DB: Registra tentativa
    API->>Q: Agenda avaliação/evento
    Q-->>API: Processamento assíncrono
    API->>DB: Atualiza XP/progresso
    API-->>W: Feedback
    W-->>A: Resultado + evolução

    opt Mentoria IA
        A->>W: Solicita ajuda
        W->>API: Contexto do desafio
        API->>AI: Consulta contextual
        AI-->>API: Orientação
        API-->>W: Feedback do Sensei
        W-->>A: Resposta
    end
```

---

## 4. Arquitetura de frontend

```mermaid
flowchart TB
    Routes[Routes]
    Pages[Pages]
    Features[Feature Modules]
    Components[Design System / Components]
    Hooks[Hooks]
    Query[TanStack Query]
    Store[Local UI State]
    Services[API Services]

    Routes --> Pages
    Pages --> Features
    Features --> Components
    Features --> Hooks
    Hooks --> Query
    Features --> Store
    Query --> Services
    Services --> API[Django REST API]
```

### Regra de organização

```text
routes/
   ↓
pages/
   ↓
features/
   ↓
components/
   ↓
hooks + services + query
```

O objetivo é evitar páginas gigantes e permitir evolução independente de cada área do produto.

---

## 5. Arquitetura de dados

```mermaid
flowchart TB
    User[User]
    Profile[Profile]
    Course[Course]
    Module[Module]
    Lesson[Lesson]
    Exercise[Exercise]
    Enrollment[Enrollment]
    Progress[Progress]
    Attempt[Exercise Attempt]
    XP[XP Event]
    Badge[Badge]
    Project[Portfolio Project]
    Post[Community Post]

    User --> Profile
    User --> Enrollment
    User --> Progress
    User --> Attempt
    User --> XP
    User --> Project
    User --> Post

    Course --> Module
    Module --> Lesson
    Lesson --> Exercise
    Enrollment --> Course
    Progress --> Lesson
    Attempt --> Exercise
    XP --> Badge
```

---

# Diagramas originais preservados

Os diagramas abaixo foram mantidos para preservar a documentação histórica e técnica da primeira arquitetura do projeto.

## 6. Diagrama estrutural / arquitetura de alto nível

```mermaid
flowchart LR
    Usuario[Usuário] --> Frontend[Frontend React + Vite]
    Frontend --> API[Django REST API]
    API --> BD[(Banco de Dados)]
    API --> Media[Arquivos de mídia]
    API --> Redis[(Redis)]
    API --> Celery[Workers Celery]
```

## 7. Diagrama de componentes

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

## 8. Diagrama de pacotes

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

## 9. Diagrama de classes

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

## 10. Diagrama de implantação

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

## 11. Diagrama de objetos

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

## 12. Diagrama de casos de uso

```mermaid
flowchart TD
    Usuario[Aluno] --> UC1[Entrar no sistema]
    Usuario --> UC2[Visualizar cursos]
    Usuario --> UC3[Assistir aula]
    Usuario --> UC4[Enviar resposta do desafio]
    Usuario --> UC5[Visualizar progresso]
```

## 13. Diagrama de sequência original

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

## 14. Diagrama de atividades

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

## 15. Diagrama de máquina de estados

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

## 16. Diagrama de entidade-relacionamento — DER original

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

## 17. Diagrama de fluxo de dados — DFD original

```mermaid
flowchart LR
    Usuario[Aluno] -->|envia ação| Frontend[Frontend]
    Frontend -->|requisição| API[API Django]
    API -->|consulta| DB[(Banco de Dados)]
    API -->|serve mídia| Storage[Arquivos de mídia]
    API -->|retorna dados| Frontend
    Frontend -->|apresenta feedback| Usuario
```

## 18. Visão de fluxo de conteúdo do curso

```mermaid
flowchart TD
    Curso[Curso] --> Modulo1[Módulo 1]
    Curso --> Modulo2[Módulo 2]
    Modulo1 --> Aula1[Aula de vídeo]
    Modulo1 --> Aula2[Exercício]
    Modulo2 --> Aula3[Aula de apostila]
    Modulo2 --> Aula4[Laboratório]
```

---

## 19. Matriz de evolução arquitetural

| Área | Arquitetura original | Arquitetura-alvo |
|---|---|---|
| Frontend | React/Vite | React/Vite + features + design system |
| Dados do frontend | Store/local | TanStack Query + estado local por responsabilidade |
| Backend | Core Django centralizado | Domínios Django separados |
| Aprendizagem | Course/Module/Lesson | Learning + Progress + Assessment |
| Gamificação | XP/progresso | Gamification domain + eventos |
| Comunidade | Feed | Community domain |
| Portfólio | Interface | Portfolio domain + evidências |
| IA | Evolução futura | AI Sensei + RAG + serviços especializados |
| Tarefas | Celery/Redis | Jobs assíncronos orientados a eventos |
| Arquivos | Media local | Storage desacoplado |
| Observabilidade | Básica | Logs + métricas + traces |
| Escala | Monólito modular | Monólito modular preparado para serviços quando necessário |

> **Princípio:** não transformar o Dojô em microserviços prematuramente. Primeiro modularizar o monólito, medir o comportamento e extrair serviços apenas quando houver uma necessidade real de escala, isolamento ou domínio.

---

## 20. Direção arquitetural

```text
                 🥋 DATA DRIVEN DOJÔ
                          │
          ┌───────────────┼────────────────┐
          │               │                │
       EXPERIENCE      LEARNING         COMMUNITY
          │               │                │
          └───────────────┼────────────────┘
                          │
                    APPLICATION
                          │
          ┌───────────────┼────────────────┐
          │               │                │
        DATA        GAMIFICATION          AI
          │               │                │
          └───────────────┼────────────────┘
                          │
                  PLATFORM SERVICES
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
    PostgreSQL          Redis             Celery
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                 OBSERVABILITY / CLOUD
```

### Regra de ouro

**Evoluir a arquitetura na mesma velocidade que o produto.**

O objetivo não é ter a arquitetura mais complexa. É ter a arquitetura **mais adequada ao estágio do Dojô**, permitindo que a plataforma cresça com qualidade, performance, segurança e previsibilidade.
