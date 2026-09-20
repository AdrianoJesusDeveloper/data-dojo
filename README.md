<div align="center">

<img src="docs/assets/logo-data-driven-dojo.png" alt="Data Driven Dojô" width="180" />

# Data Driven Dojô ⚔️📊

### **Aprender. Construir. Ensinar. Evoluir.**

Plataforma local-first de aprendizagem, produção e prática profissional em **Dados, IA, Engenharia, Cloud e Automação**, construída como um ecossistema integrado de estudo, execução e criação.

**Determinação · Disciplina · Direção · Kaizen**

<br>

![React](https://img.shields.io/badge/React-19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-20232A?style=for-the-badge&logo=typescript&logoColor=3178C6)
![Django](https://img.shields.io/badge/Django-6-20232A?style=for-the-badge&logo=django&logoColor=44B78B)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-20232A?style=for-the-badge&logo=postgresql&logoColor=4169E1)
![Celery](https://img.shields.io/badge/Celery-5-20232A?style=for-the-badge&logo=celery&logoColor=37814A)
![Redis](https://img.shields.io/badge/Redis-Local-20232A?style=for-the-badge&logo=redis&logoColor=DC382D)

</div>

---

## 🧭 O que é o Data Driven Dojô

O **Data Driven Dojô** é um ambiente integrado para transformar estudo em competência prática.

A proposta central é simples:

```text
Fundamento → Prática → Projeto → Evidência → Conteúdo → Evolução
```

Em vez de separar aprendizado, portfólio, produção de conteúdo, pesquisa e execução profissional em ferramentas isoladas, o Dojô conecta tudo em um mesmo fluxo.

Hoje o projeto funciona principalmente como uma aplicação **local-first**, executada no computador do operador, com módulos privados para estudo, produção e trabalho.

---

## 🧩 Ecossistema 3DS

O projeto está evoluindo em torno de quatro núcleos conectados:

### 📚 Biblioteca do Sensei

Biblioteca privada para estudo, pesquisa e RAG.

Principais capacidades atuais:

- catálogo visual de livros;
- PDF, EPUB, DOCX e TXT;
- OCR de PDFs escaneados e mistos;
- extração de texto, chunks e embeddings;
- deduplicação por SHA-256;
- capas automáticas e mídia associada;
- busca interna;
- progresso de leitura;
- marcadores;
- anotações;
- destaques;
- índice automático;
- índice manual editável;
- Reader integrado para PDF e formatos textuais;
- **Narrador V1 local**, usando as vozes disponíveis no navegador/sistema;
- processamento assíncrono com Celery + Redis;
- integração do acervo com fluxos de RAG.

> O arquivo original do livro é preservado. Índices, progresso, marcações, traduções futuras e demais metadados são tratados como camadas separadas.

### 🔎 Curadoria de Fontes V2

A ponte entre a Biblioteca do Sensei e o conteúdo didático agora possui um fluxo explícito de curadoria humana:

- busca de fontes já processadas no acervo local;
- seleção de livro/fonte para a unidade de estudo;
- confirmação humana de capítulo, seção, páginas ou trecho;
- objetivo e justificativa editorial obrigatórios;
- criação de proposta antes da aprovação;
- aprovação/rejeição humana;
- bloqueio `NEEDS_SOURCE` mantido quando a formação exige fonte aprovada;
- liberação da geração didática imediatamente após aprovação;
- recuperação de trechos relevantes do livro aprovado via RAG para fundamentar a aula;
- preservação da proveniência por livro e página;
- nenhuma fonte é aprovada automaticamente pela IA.
- fontes rejeitadas podem ser corrigidas e reenviadas sem criar vínculo duplicado;
- tentativas de duplicar uma proposta já ativa retornam conflito controlado, nunca erro 500.

> A IA pode ajudar a localizar e usar o acervo, mas a decisão sobre o que se torna fonte oficial da unidade continua humana.

> **Validação funcional da Curadoria de Fontes V2:** fluxo testado em uso real com fonte local processada, proposta revisada, aprovação humana e geração de aula em DRAFT via Groq. A validação editorial da qualidade/proveniência do conteúdo gerado continua sendo uma etapa humana separada.

### 🧾 Grounding Auditável V1

A geração didática baseada na Biblioteca agora aplica uma camada adicional de rastreabilidade:

- intervalos aprovados são armazenados em formato estruturado por páginas físicas do PDF;
- o RAG é restrito aos ranges aprovados pela curadoria humana;
- geração com fonte local é bloqueada quando nenhum trecho é encontrado dentro dos ranges aprovados;
- cada aula gerada preserva um snapshot do grounding realmente enviado ao provider;
- o snapshot registra fonte, livro, página PDF, chunk, trecho, provider, modelo e data da geração;
- o snapshot V2 também preserva o contexto pedagógico confiável da geração e um fingerprint SHA-256 desse contexto;
- respostas estruturalmente válidas, mas semanticamente desalinhadas com unidade/objetivos/fontes, são rejeitadas antes de serem salvas (`SEMANTIC_MISMATCH`); a checagem específica de objetivos só é aplicada quando o contexto pedagógico possui vocabulário suficiente, evitando falso positivo em rascunhos genéricos;
- validação real do piloto registrou snapshot V2 com fingerprint de contexto, provider/modelo, 1 fonte e 8 trechos; páginas usadas: 79, 81, 98, 122, 128, 134, 136 e 138, todas dentro dos ranges PDF aprovados;
- aulas geradas com fontes aprovadas e sem snapshot precisam ser regeneradas antes de entrar em revisão editorial; aulas humanas sem fonte continuam seguindo o fluxo editorial normal;
- o Content Studio exibe a proveniência do grounding na própria interface;
- o rascunho pode ser regenerado com as fontes e ranges aprovados mais recentes;
- marcadores provisórios como `Capítulo X`, `XX–YY` e `a confirmar` não podem ser aprovados.

> Para fontes locais, a página operacional é sempre a página física do PDF/Reader. A paginação impressa pode continuar registrada no texto de localização como referência bibliográfica complementar.

> **Backfill real validado:** a fonte piloto de *Aprendendo Python* foi convertida para ranges físicos `122–135`, `136–152`, `79–99` e `98`. A paginação impressa registrada em texto livre, inclusive um valor digitado incorretamente, não foi interpretada como range operacional.

### 🔗 Claim-Level Grounding V1

Gerações novas em `APPROVED_SOURCES` validam as afirmações contra os
`approved_source_excerpts` da **mesma geração**, mantendo o Grounding Snapshot V2
e seu fingerprint inalterados. A implementação usa os JSONFields existentes;
nenhuma migration foi adicionada (última migration: `0034_grounding_ranges_snapshot`).

- O contrato do provider recebe `metadata.claims`, com `text` e `evidence`:
  `source_id` (ID de `SenseiUnitSource`), `book_id`, `chunk_id`, `pdf_page` e `quote`.
- Todos os identificadores e a página física devem corresponder ao mesmo trecho
  do snapshot atual. Um chunk real fora desse conjunto também é rejeitado.
- **V1 extrativa e conservadora:** `text` deve ser igual a `quote`, e a citação
  deve existir literalmente no trecho enviado ao provider. IDs válidos ou
  similaridade lexical não certificam uma paráfrase nem uma afirmação nova.
- Seções factuais devem ter conteúdo integralmente coberto pelos claims, unidos
  por duas quebras de linha. Texto adicional, citação inventada, evidência ausente
  ou identidade divergente produz `CLAIM_GROUNDING_INVALID` (HTTP 409), sem
  persistir a geração inválida. Falha de regeneração preserva a versão anterior.
- Objetivos, prática guiada, exercícios, autoria, projetos, reflexão,
  autoavaliação e critérios de domínio podem usar `claims: []`. Esses textos são
  identificados como **orientação pedagógica, não como afirmações da fonte**;
  premissas factuais devem ser separadas em seções sustentadas por evidência.
- `REFERENCES` é construída pelo backend a partir das evidências verificadas;
  referências livres propostas pelo modelo não são fonte de verdade.
- O resultado é registrado em `metadata.claim_grounding`, incluindo versão,
  classificação, tipo de validação e evidências canônicas. O Content Studio
  permite consultar afirmação, livro, página PDF, chunk, fonte e trecho contextual.
- Edições humanas removem a certificação anterior da redação substituída, sem
  alterar o snapshot histórico. Aulas humanas e `AI_GENERATED_UNSOURCED` mantêm
  seu fluxo editorial. Aulas antigas não recebem certificação retroativa.
- A guarda editorial no backend bloqueia `REVIEW` e `APPROVED` para aulas com
  fontes aprovadas e proveniência de IA sem estado válido de claim grounding em
  todas as seções, **mesmo com Snapshot V2 presente**. Uma aula piloto legada já
  em REVIEW também recebe HTTP 409 e orientação para regenerar com Claim-Level
  Grounding atual. Retorne-a a DRAFT antes de usar a regeneração existente.
  O backend revalida as afirmações contra o snapshot histórico, não aceita
  metadados enviados no mesmo PATCH como atalho e preserva `human_edited` como
  estado humano explicitamente não certificado durante revisão/aprovação.

**Limitações:** correspondência extrativa não é um verificador geral de verdade,
interpretação ou implicação lógica. Citações podem ser selecionadas fora de
contexto; títulos e premissas embutidas nas instruções ainda exigem revisão humana.
Paráfrases factuais são rejeitadas nesta V1. Fontes apenas bibliográficas, sem
trecho recuperado no snapshot, não bastam para uma nova geração grounded.
O guard `SEMANTIC_MISMATCH` continua independente: sua heurística temática não
é usada como prova de sustentação factual. Não houve nova chamada externa,
modelo avaliador, fila, serviço ou alteração na arquitetura local.

**Validação automatizada (2026-09-20):**

- `python .\apps\api\manage.py check`: aprovado;
- `python .\apps\api\manage.py makemigrations --check`: nenhuma alteração detectada;
- compilação Python: aprovada;
- 48 testes focados de conteúdo didático/curadoria/RAG: aprovados;
- 16 testes frontend: aprovados;
- `npm run typecheck`: aprovado;
- `npm run build`: aprovado;
- suíte completa `library.tests`: **279 testes executados, OK, com 1 skipped** por ausência de privilégio para symlink no Windows;
- o teste anteriormente incompatível de `SenseiFormation` foi atualizado para respeitar a exigência atual de range PDF estruturado e passou isoladamente e na suíte completa;
- os testes utilizaram banco de teste isolado criado e destruído pelo Django; o PostgreSQL principal não foi alterado;
- a guarda editorial está incluída nos testes focados, inclusive o piloto legado já em REVIEW, a tentativa de enviar certificação no mesmo PATCH, metadados inválidos, edição humana e preservação do snapshot.

O build concluiu com avisos já conhecidos sobre `::highlight`, bundles maiores que 500 kB e opção `platform` do empacotador; esses componentes/configurações não foram alterados nesta entrega.

**Ainda não validado em uso real.** O operador deverá regenerar um rascunho com
fontes aprovadas, abrir “Ver evidências das afirmações”, conferir cada passagem
no livro/PDF e revisar também as premissas dos exercícios. Depois, testar
DRAFT → REVIEW → APPROVED. A aprovação editorial não é automática.

### 🧠 Content Studio

Ambiente privado para pesquisa, planejamento editorial e geração assistida por IA.

Inclui:

- projetos editoriais;
- Dossiê Mestre;
- pesquisa fundamentada;
- planos versionados;
- geração de módulos, aulas e vídeos;
- Conselho Editorial multiagente;
- aprovação humana;
- histórico de versões;
- Teleprompter;
- exportações por seção;
- suporte a múltiplos providers de IA.

A IA propõe e acelera. **A decisão final permanece humana.**

### 💼 Project Studio

Ambiente de apoio à execução profissional.

Direção do módulo:

- organizar oportunidades;
- registrar briefing;
- estruturar execução;
- produzir entregáveis;
- reunir evidências;
- transformar trabalhos reais em competências e portfólio;
- apoiar atividades freelancer e geração de renda.

### 🤖 IA Sensei

Camada de mentoria e orquestração do ecossistema.

O objetivo não é substituir o aprendizado, mas orientar:

- o que estudar;
- o que construir;
- como validar;
- como transformar aprendizado em projeto;
- como transformar projeto em conteúdo;
- como transformar experiência em evidência profissional.

---

## 🏗️ Arquitetura atual

```text
┌──────────────────────────────────────────────────────────────┐
│                    DATA DRIVEN DOJÔ                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  React + TypeScript + Vite                                  │
│  ├── TanStack Router                                         │
│  ├── TanStack Query                                          │
│  ├── Tailwind CSS                                            │
│  └── Radix UI                                                │
│                         │                                    │
│                         ▼                                    │
│                Django REST Framework                         │
│  ├── Core educacional                                       │
│  ├── Biblioteca do Sensei                                   │
│  ├── Content Studio                                         │
│  ├── Professional / Project Studio                          │
│  ├── IA / Providers                                         │
│  └── 3DStore                                                │
│                         │                                    │
│              ┌──────────┴──────────┐                         │
│              ▼                     ▼                         │
│        PostgreSQL 18             Redis                       │
│                                     │                        │
│                                     ▼                        │
│                               Celery Worker                  │
└──────────────────────────────────────────────────────────────┘
```

### Estratégia local-first

No estágio atual:

- PostgreSQL roda localmente;
- Redis roda localmente/WSL;
- Celery executa tarefas assíncronas;
- Content Studio, Project Studio e Biblioteca do Sensei são privados;
- o acervo permanece no computador do operador;
- Docker não é requisito para o fluxo principal atual;
- a arquitetura permanece preparada para futura expansão sem forçar migração prematura.

---

## 🧱 Stack técnica

### Frontend

`React 19` · `TypeScript 5` · `Vite 7` · `TanStack Router` · `TanStack Query` · `Tailwind CSS` · `Radix UI`

### Backend

`Python` · `Django 6` · `Django REST Framework` · `Celery` · `dj-rest-auth`

### Dados e processamento

`PostgreSQL 18` · `Redis` · `PyMuPDF` · `pytesseract` · `Pillow` · `sentence-transformers`

### IA

Arquitetura preparada para providers configuráveis, incluindo integrações compatíveis com:

`OpenAI` · `Gemini` · `DeepSeek` · `Anthropic` · endpoints compatíveis

---

## 📚 Biblioteca do Sensei — estado atual

### Ingestão e catálogo

- [x] cadastro de fontes;
- [x] processamento de livros;
- [x] OCR por página;
- [x] suporte a PDFs mistos;
- [x] deduplicação por hash;
- [x] tratamento de duplicidade no upload;
- [x] lifecycle de livros;
- [x] favoritos;
- [x] capas e thumbnails;
- [x] grid/lista;
- [x] filtros;
- [x] busca visual;
- [x] status de disponibilidade;
- [x] progresso de processamento.

### Reader

- [x] PDF integrado;
- [x] EPUB;
- [x] DOCX;
- [x] TXT;
- [x] navegação;
- [x] zoom;
- [x] modo leitura;
- [x] tela cheia;
- [x] continuar de onde parou;
- [x] marcadores;
- [x] anotações;
- [x] destaques;
- [x] busca interna;
- [x] índice manual editável;
- [x] índice automático;
- [x] Narrador V1 implementado;
- [x] Narrador V1 validado em uso real;
- [x] persistência do índice manual validada ao sair e reabrir o Reader;
- [ ] Tradutor V1;
- [x] Curadoria de Fontes V2 integrada ao plano de estudo;
- [x] Curadoria de Fontes V2 validada em uso real até a geração da aula com fonte aprovada;
- [x] RAG restrito aos intervalos PDF aprovados;
- [x] snapshot auditável de grounding por aula;
- [x] regeneração de rascunho com grounding atual;
- [x] migration 0034 aplicada no PostgreSQL principal e backfill de ranges PDF validado em uso real;
- [x] regenerar a aula piloto e validar ranges/chunks do grounding em uso real;
- [x] geração piloto repetida após o guard semântico: snapshot V2, contexto pedagógico, 1 fonte, 8 trechos e páginas PDF restritas aos ranges aprovados validados em uso real;
- [ ] modo Original / Traduzido / Lado a lado;
- [ ] integração Narrador + tradução.


> **Validação concluída em 2026-09-19:** o índice manual permaneceu salvo após sair e reabrir o Reader, e o Narrador V1 foi testado com sucesso em uso real.

### Narrador V1

O Narrador foi projetado para funcionar sem obrigar o uso de API paga.

Capacidades:

- ouvir página/seção atual;
- continuar áudio;
- pausar;
- parar;
- avançar/voltar;
- velocidade de 0,5× a 2×;
- escolha de idioma;
- escolha de voz disponível no sistema;
- retomada local da posição de áudio;
- destaque do trecho narrado quando suportado;
- fallback para texto extraído/OCR.

---

## 🧪 Qualidade e validação

O projeto usa validação incremental antes de promover mudanças.

### Frontend

```powershell
npm run typecheck
npm run build
```

### Backend

```powershell
python .\apps\api\manage.py check
python .\apps\api\manage.py makemigrations --check
python .\apps\api\manage.py test library.tests -v 2
```

Estado recente da Biblioteca:

- histórico anterior: **245 testes** da suíte completa aprovados;
- execução atual do Claim-Level Grounding V1: **279 testes executados na suíte completa, OK, com 1 skipped** por limitação de symlink no ambiente Windows;
- **13 testes focados** do Reader/Media aprovados após o índice manual;
- PostgreSQL principal migrado até **library.0034_grounding_ranges_snapshot**;
- backups validados com `pg_dump` + `pg_restore --list`.

---

## 🧠 Princípios de produto

### 1. Fundamentos antes de abstrações

O Dojô não existe para esconder a tecnologia. Existe para ajudar a compreendê-la e usá-la melhor.

### 2. IA como amplificador

A IA orienta, revisa, questiona, sugere e automatiza tarefas operacionais, mas não substitui julgamento humano, estudo e validação.

### 3. Aprender fazendo

Toda trilha deve convergir para prática, projeto, evidência ou conteúdo.

### 4. Local-first quando isso fizer sentido

Privacidade, controle do acervo e baixo custo operacional são prioridades reais nesta fase.

### 5. Evolução incremental

O projeto evita reescritas desnecessárias. Cada sprint deve deixar o sistema mais utilizável e verificável.

### 6. Kaizen

Melhoria contínua é parte da arquitetura, do produto e do método de aprendizagem.

---

## 🔐 Privacidade e segurança operacional

As áreas privadas do ecossistema são tratadas como ferramentas de uso interno.

Diretrizes atuais:

- segredos ficam em variáveis de ambiente;
- livros e arquivos privados não são publicados;
- Content Studio, Project Studio e Biblioteca não expõem conteúdo de trabalho a terceiros;
- operações críticas usam confirmação explícita;
- uploads passam por validação;
- o acervo original é preservado;
- traduções futuras serão armazenadas como derivados locais, nunca sobrescrevendo o original.

---

## 🗺️ Roadmap estratégico

### 🟢 Base consolidada

- [x] autenticação;
- [x] cursos, módulos e aulas;
- [x] workspace;
- [x] comunidade;
- [x] dashboard;
- [x] gamificação;
- [x] API Django REST;
- [x] RAG da Biblioteca;
- [x] jobs assíncronos;
- [x] Content Studio privado;
- [x] Project/Professional Studio base;
- [x] Conselho Editorial;
- [x] Reader avançado.

### 🔵 Foco atual — Biblioteca do Sensei

- [x] visualização moderna;
- [x] reader;
- [x] anotações e destaques;
- [x] índice editável;
- [x] narrador local V1;
- [x] persistência do índice manual validada em uso real;
- [ ] Tradutor V1;
- [ ] tradução por trecho/página;
- [ ] cache local de traduções;
- [ ] lado a lado original/tradução;
- [ ] narrar original ou tradução.

### 🟣 Próximos ciclos

- [ ] fechar UX da Biblioteca;
- [ ] ampliar Project Studio;
- [ ] consolidar evidências profissionais;
- [ ] reforçar Content Studio multiformato;
- [ ] observabilidade;
- [ ] E2E;
- [ ] CI/CD;
- [ ] preparação gradual para hospedagem futura.

---

## 🧭 Fluxo de trabalho do projeto

```text
Ideia
  ↓
Backlog
  ↓
Implementação em branch de trabalho
  ↓
Testes focados
  ↓
Teste completo
  ↓
Validação manual
  ↓
Backup/migration quando necessário
  ↓
Curadoria de fontes aprovada antes da geração didática quando exigida
  ↓
Atualização do README
  ↓
Promoção de branch
```

> O README é tratado como **documentação viva**. Mudanças relevantes no repositório devem atualizar também a documentação, o estado funcional e o roadmap.

---

## 🗂️ Estrutura principal

```text
src/
├── routes/
├── pages/
├── components/
│   └── library/
├── hooks/
├── lib/
├── assets/
└── tests/

apps/api/
├── core/
├── ai/
├── store/
├── library/
├── professional/
└── config/
```

---

## 🚀 Execução local

O fluxo principal atual usa serviços locais.

### Frontend

```powershell
npm run dev
```

A interface principal é iniciada normalmente em:

```text
http://localhost:8080/
```

### Django

```powershell
python .\apps\api\manage.py runserver 127.0.0.1:8000
```

### Celery

```powershell
celery -A config worker --loglevel=INFO --pool=solo
```

### Serviços esperados

| Serviço | Uso |
|---|---|
| Frontend | Interface React |
| Django | API e regras de negócio |
| PostgreSQL | Banco principal |
| Redis | Broker/cache |
| Celery | Processamento assíncrono |

> Os scripts locais de inicialização podem configurar automaticamente variáveis e conexões específicas do ambiente do operador.

---

## 📸 Showcase

A pasta `docs/screenshots/` é reservada para capturas reais das áreas principais:

```text
docs/
├── assets/
│   └── logo-data-driven-dojo.png
└── screenshots/
    ├── 01-home.png
    ├── 02-dashboard.png
    ├── 03-trilhas.png
    ├── 04-cursos.png
    ├── 05-workspace.png
    ├── 06-progressao.png
    ├── 07-comunidade.png
    ├── 08-portfolio.png
    ├── 09-ai-sensei.png
    └── 10-responsive.png
```

---

## 🎯 Visão

O Data Driven Dojô não pretende ser apenas uma plataforma de cursos.

A visão é construir um ambiente onde seja possível:

- aprender;
- pesquisar;
- praticar;
- produzir;
- trabalhar;
- registrar evidências;
- ensinar;
- evoluir continuamente.

Tudo conectado pela mesma filosofia:

> **Determinação para começar.**  
> **Disciplina para continuar.**  
> **Direção para evoluir.**

---

<div align="center">

### 🥋 Data Driven Dojô

**Treinar. Construir. Ensinar. Evoluir.**

**Kaizen — um passo melhor a cada dia.**

</div>
