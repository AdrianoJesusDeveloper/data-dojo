<div align="center">

# 🥋 Data Driven Dojô

### **Treine fundamentos. Construa projetos. Evolua com Kaizen.**

Uma plataforma educacional gamificada para formar profissionais de **dados, engenharia, IA e tecnologia** por meio de prática deliberada, desafios e progressão por faixas.

<br>

**Determinação · Disciplina · Dedicação**

<br><br>

[![React](https://img.shields.io/badge/React-19-1C1C1C?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-1C1C1C?style=for-the-badge&logo=typescript&logoColor=3178C6)](https://www.typescriptlang.org/)
[![Django](https://img.shields.io/badge/Django-1C1C1C?style=for-the-badge&logo=django&logoColor=44B78B)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-1C1C1C?style=for-the-badge&logo=postgresql&logoColor=4169E1)](https://www.postgresql.org/)
[![AWS](https://img.shields.io/badge/AWS-1C1C1C?style=for-the-badge&logo=amazonaws&logoColor=FF9900)](https://aws.amazon.com/)

</div>

---

## 🥋 A visão do Dojô

O **Data Driven Dojô** nasceu de uma ideia simples: aprender tecnologia não deve ser apenas consumir cursos. Deve ser uma jornada de **fundamentos → prática → desafio → feedback → evolução**.

A experiência combina:

- 🎓 **Trilhas de aprendizagem** para organizar conhecimento;
- ⚔️ **Desafios e exercícios** para transformar teoria em prática;
- 🟠 **Pontos Kaizen (XP)** para tornar evolução visível;
- 🥋 **Sistema de faixas** para representar progressão;
- 📈 **Dashboard de progresso** para acompanhar consistência;
- 🧪 **Workspace** para aprender fazendo;
- 👥 **Comunidade** para compartilhar a jornada;
- 🤖 **IA** como camada futura de mentoria e personalização.

> **O Dojô não quer formar apenas usuários de ferramentas. Quer formar profissionais capazes de pensar, construir e resolver problemas.**

---

## 🎯 Posicionamento estratégico

O produto está sendo estruturado como uma plataforma de **Learning Experience + Practice + Community**, com potencial de evoluir para um ecossistema de formação profissional.

### Público prioritário

**Iniciantes e profissionais em transição/evolução para Data & Analytics, Data Engineering, AI Engineering e Full Stack.**

### Proposta de valor

| Problema | Resposta do Dojô |
|---|---|
| Cursos fragmentados | Trilhas organizadas por competências |
| Pouca prática | Exercícios e desafios dentro da plataforma |
| Progresso invisível | XP, faixas, streak e indicadores |
| Falta de feedback | Avaliação estruturada dos desafios |
| Aprendizado solitário | Comunidade e jornada compartilhada |
| Excesso de teoria | Workspace orientado à execução |
| IA sem direção | IA aplicada como mentora e camada de personalização |

---

## 🧭 Jornada do aluno

```text
                    🥋 ENTRAR NO DOJÔ
                           │
                           ▼
                  🎯 DEFINIR OBJETIVO
                           │
                           ▼
                    📚 TRILHA DE ESTUDO
                           │
                           ▼
                    🧠 APRENDER FUNDAMENTO
                           │
                           ▼
                    ⚔️ PRATICAR / DESAFIAR
                           │
                           ▼
                    📝 RECEBER FEEDBACK
                           │
                           ▼
                    🟠 GANHAR XP / KAIZEN
                           │
                           ▼
                    🥋 AVANÇAR DE FAIXA
                           │
                           ▼
                    🏗️ CONSTRUIR PROJETOS
                           │
                           ▼
                    💼 PORTFÓLIO / CARREIRA
                           │
                           └──────────► KAIZEN ♻️
```

---

## 🏗️ Arquitetura atual

```text
┌─────────────────────────────────────────────────────────────┐
│                     DATA DRIVEN DOJÔ                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  React + TypeScript + Vite                                 │
│  ├── TanStack Router                                        │
│  ├── TanStack Query                                         │
│  ├── Tailwind CSS                                           │
│  ├── Componentes reutilizáveis                              │
│  └── Store / experiência gamificada                         │
│                         │                                   │
│                         ▼                                   │
│                 Django REST Framework                        │
│  ├── Autenticação                                            │
│  ├── Cursos / módulos / aulas                               │
│  ├── Exercícios e avaliação                                 │
│  └── API de conteúdo                                        │
│                         │                                   │
│              ┌──────────┴──────────┐                        │
│              ▼                     ▼                        │
│        PostgreSQL               Redis                       │
│                                    │                        │
│                                    ▼                        │
│                              Celery Workers                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Camadas

**Frontend** — experiência, navegação, gamificação e interação.

**API** — regras de negócio, autenticação e entrega de conteúdo.

**Dados** — PostgreSQL como base principal e Redis para necessidades de cache/filas.

**Workers** — Celery preparado para tarefas assíncronas e evolução da plataforma.

---

## ⚙️ Stack

### Frontend

`React` · `TypeScript` · `Vite` · `TanStack Router` · `TanStack Query` · `Tailwind CSS`

### UX & UI

`Radix UI` · `Lucide` · `Recharts` · `Sonner`

### Backend

`Python` · `Django` · `Django REST Framework` · `dj-rest-auth`

### Dados & infraestrutura

`PostgreSQL` · `SQLite (dev)` · `Redis` · `Celery`

### Qualidade

`TypeScript Strict` · `ESLint` · `Prettier` · `Vitest` · `Testing Library`

---

## ✨ Funcionalidades

### 🎓 Aprendizagem

- Cadastro de cursos;
- módulos e aulas;
- vídeos e conteúdo textual;
- exercícios estruturados;
- critérios de avaliação;
- workspace de desafios.

### 🥋 Gamificação

- XP / Pontos Kaizen;
- progresso por faixa;
- streak;
- indicadores de horas e evolução;
- feedback visual;
- celebrações de progressão.

### 👥 Comunidade

- feed;
- posts;
- curtidas;
- comentários;
- interação social.

### 📊 Dashboard

A plataforma transforma atividade de aprendizagem em sinais de progresso para ajudar o aluno a responder:

**Onde estou? · O que estou aprendendo? · Quanto pratiquei? · Qual é o próximo passo?**

---

## 🚀 Usabilidade, performance e responsividade

A evolução atual prioriza uma experiência consistente em **desktop, tablet e mobile**, sem abandonar a identidade visual do Dojô.

### Usabilidade

- hierarquia visual orientada à tarefa;
- estados de carregamento e erro mais claros;
- navegação previsível;
- foco de teclado visível;
- alvos de toque adequados;
- mensagens de erro em português e orientadas à ação;
- jornada reduzida entre conteúdo, prática e feedback.

### Performance

- cache de queries com TanStack Query;
- revalidação controlada;
- preloading por intenção de navegação;
- menor refetch desnecessário ao retornar à janela;
- tipagem estática como barreira preventiva contra regressões;
- fontes carregadas somente nas famílias realmente utilizadas;
- suporte a redução de movimento para diminuir custo visual e melhorar acessibilidade.

### Responsividade

A base visual mantém o comportamento fluido e adiciona cuidados para telas compactas:

- viewport preparado para dispositivos móveis;
- prevenção de overflow horizontal;
- mídias responsivas;
- tipografia adaptada em telas pequenas;
- interações compatíveis com toque;
- navegação preparada para evolução mobile-first.

> **A identidade não foi redesenhada. Foi organizada para funcionar melhor em mais contextos.**

---

## 🎨 Identidade do Dojô — preservada

A evolução técnica **não altera a essência visual**.

### Tipografia oficial

- **Exo 2** — títulos e identidade;
- **Open Sans** — interface e leitura;
- **Roboto Mono** — código, dados e elementos técnicos.

### Paleta oficial

- `#1C1C1C` — Graphite / fundo;
- `#242424` — cards;
- `#0057B8` — Deep Blue / ação;
- `#E63946` — Samurai / energia e alertas;
- `#FFA500` — Kaizen / progresso e destaque;
- `#E5E5E5` — texto principal.

A linguagem visual continua baseada na combinação de **dojo, samurai, disciplina e Kaizen**.

---

## 🧩 Arquitetura de código

A organização segue uma separação clara entre **rotas e páginas**:

```text
src/
├── routes/          # URLs e composição de rotas
├── pages/           # Componentes visuais das páginas
├── components/      # Componentes reutilizáveis
├── hooks/           # Hooks compartilhados
├── lib/             # Estado, helpers e serviços
├── assets/          # Recursos visuais
└── tests/           # Testes

apps/api/
├── core/            # Domínio, models, serializers e views
└── config/          # Configuração Django
```

> **Princípio arquitetural:** `routes/` define o endereço e importa a página; `pages/` concentra a composição visual; regras reutilizáveis ficam fora das rotas.

---

## 📈 Escalabilidade: direção do produto

O objetivo não é apenas fazer a aplicação crescer em número de telas. É criar uma arquitetura capaz de crescer em **conteúdo, usuários, funcionalidades e negócio**.

### Evolução planejada

```text
MVP
 │
 ├── Conteúdo estruturado
 ├── Gamificação
 ├── Workspace
 └── Comunidade
       │
       ▼
PLATAFORMA
 │
 ├── Perfis de aprendizagem
 ├── Trilhas por carreira
 ├── Avaliação avançada
 ├── Projetos práticos
 └── Métricas de retenção
       │
       ▼
ECOSSISTEMA
 │
 ├── IA Sensei
 ├── Personalização
 ├── Mentoria
 ├── Certificações
 ├── Portfólio profissional
 └── Integrações / APIs
```

A separação entre frontend, API, dados e workers já cria uma base adequada para essa evolução sem exigir que a experiência do aluno seja reescrita a cada nova funcionalidade.

---

## 🗺️ Roadmap estratégico

### 🟢 Fundamentos

- [x] Autenticação
- [x] Cursos, módulos e aulas
- [x] Exercícios estruturados
- [x] Dashboard de progresso
- [x] Gamificação inicial
- [x] Workspace
- [x] Comunidade
- [x] API Django REST

### 🟡 Produto

- [ ] Progresso persistido por usuário e aula
- [ ] Avaliação de desafios mais robusta
- [ ] Trilhas por competência
- [ ] Onboarding orientado ao objetivo profissional
- [ ] Melhorias mobile
- [ ] Observabilidade de produto

### 🔵 Escala

- [ ] Cache estratégico
- [ ] Jobs assíncronos para tarefas pesadas
- [ ] Testes E2E
- [ ] CI/CD
- [ ] Observabilidade técnica
- [ ] Segurança e gestão de permissões

### 🟠 IA Sensei

- [ ] Mentoria contextual
- [ ] Feedback personalizado
- [ ] Geração de exercícios
- [ ] Recomendações de trilha
- [ ] RAG sobre conteúdo do Dojô
- [ ] Agentes especializados

### 🟣 Mercado

- [ ] Portfólio orientado a carreira
- [ ] Certificações e badges verificáveis
- [ ] Métricas de competência
- [ ] Experiências B2C / B2B
- [ ] Integrações com ecossistema profissional

---

## 🧪 Desenvolvimento local

### Pré-requisitos

- Node.js `>=18`
- Python
- PostgreSQL para ambiente completo ou SQLite para desenvolvimento local
- Redis quando utilizando tarefas assíncronas

### Frontend

```bash
npm install
npm run dev
```

Acesse `http://localhost:5173`.

### Backend

```bash
cd apps/api
python -m venv .venv
```

**Windows:**

```bash
.venv\Scripts\activate
```

Depois:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Qualidade antes de publicar

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

---

## 📐 Princípios de engenharia

**1. Fundamentos antes de abstrações**  
A tecnologia deve servir ao problema.

**2. Experiência antes da complexidade**  
Uma funcionalidade boa é aquela que o aluno entende e consegue usar.

**3. Performance é parte da UX**  
Tempo de resposta, cache e carregamento fazem parte do produto.

**4. Segurança por padrão**  
Segredos não pertencem ao código e permissões devem ser explícitas.

**5. Observabilidade antes de escala**  
Não se escala aquilo que não se consegue medir.

**6. Kaizen**  
Cada versão deve ser melhor que a anterior sem perder a essência.

---

## 🥋 A filosofia

> **Determinação para começar.**  
> **Disciplina para continuar.**  
> **Dedicação para dominar.**

O Data Driven Dojô é mais do que uma aplicação. É um experimento contínuo sobre **como aprender tecnologia de forma prática, mensurável e sustentável**.

**Treinar. Construir. Ensinar. Evoluir.**

---

<div align="center">

### 🥋 Data Driven Dojô

**Kaizen — um passo melhor a cada dia.**

</div>
