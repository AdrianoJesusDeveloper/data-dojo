from django.db import migrations


SLUG = "engenharia-ia-arquitetura-sistemas-inteligentes"


# Fonte curricular: .private-docs/TRILHA_ENGENHARIA_DE_IA.md, reorganizada por
# pré-requisitos. Este seed descreve resultados de aprendizagem, não aulas.
CURRICULUM = [
    ("Fundamentos matemáticos e computacionais", "Construir a base de Python, algoritmos e matemática necessária para raciocinar sobre modelos.",
     ["Python, tipos e estruturas de dados", "Vetores, matrizes e produto escalar", "Probabilidade, cálculo, softmax e otimização"],
     [("Implementar fundamentos computacionais reproduzíveis", 4, ["Escreve código Python tipado e testável", "Analisa complexidade e falhas", "Reproduz resultados em ambiente isolado"]), ("Explicar a matemática usada por modelos", 5, ["Opera vetores e matrizes", "Relaciona produto escalar, derivadas e otimização", "Justifica o papel da softmax"]) ]),
    ("Fundamentos de IA e Machine Learning", "Distinguir paradigmas de IA e construir baselines de aprendizado de máquina orientados ao custo do erro.",
     ["IA, automação, ML e ciclo experimental", "Regressão, classificação e clustering", "Validação, métricas e análise de erro"],
     [("Projetar experimentos de Machine Learning", 5, ["Define baseline e hipótese", "Separa treino, validação e teste sem vazamento", "Escolhe métricas pelo custo do erro"]), ("Implementar pipelines clássicos de ML", 4, ["Constrói pipeline reproduzível", "Compara modelos e hiperparâmetros", "Depura overfitting e underfitting"]) ]),
    ("Deep Learning", "Compreender e implementar redes neurais com treinamento, regularização e rastreabilidade.",
     ["Tensores, camadas e funções de ativação", "Loss, backpropagation e otimizadores", "Regularização e rastreamento de experimentos"],
     [("Implementar e depurar redes neurais", 4, ["Constrói uma rede e seu loop de treino", "Diagnostica gradientes e overfitting", "Registra parâmetros e resultados"]), ("Justificar decisões de Deep Learning", 5, ["Relaciona arquitetura ao problema", "Avalia custo computacional e viés", "Defende regularização e estratégia de treino"]) ]),
    ("Transformers e LLMs", "Derivar a arquitetura Transformer e compreender capacidades e limites de grandes modelos de linguagem.",
     ["Tokenização, embeddings posicionais e contexto", "Q/K/V, self-attention e multi-head attention", "Blocos Transformer, pré-treino e inferência de LLMs"],
     [("Explicar self-attention do vetor ao Transformer", 5, ["Deriva Q, K e V a partir de representações", "Explica escala, softmax e máscaras", "Relaciona atenção aos blocos Transformer"]), ("Analisar capacidades e limites de LLMs", 5, ["Explica pré-treino e inferência", "Identifica limites de contexto e alucinação", "Justifica quando não usar um LLM"]) ]),
    ("Engenharia de LLMs e Prompting", "Tratar prompts, contexto e saídas como contratos versionados e testáveis.",
     ["Mensagens, instruções e gestão de contexto", "Saída estruturada, schemas e validação", "Templates, cache, fallback e guardrails"],
     [("Projetar contratos de interação com LLMs", 5, ["Separa instrução, dados e contexto", "Valida saída estruturada", "Versiona prompts e casos de teste"]), ("Depurar aplicações baseadas em LLM", 4, ["Reproduz falhas de instrução", "Trata timeout, limite e resposta inválida", "Mede latência, custo e qualidade"]) ]),
    ("Embeddings e Recuperação de Informação", "Construir busca semântica antes de compor sistemas RAG.",
     ["Embeddings e métricas de similaridade", "Índices vetoriais, filtros e metadados", "Chunking, retrieval e avaliação de relevância"],
     [("Implementar recuperação vetorial", 4, ["Gera e versiona embeddings", "Configura índice e filtros", "Recupera resultados com metadados rastreáveis"]), ("Avaliar recuperação de informação", 5, ["Cria conjunto de consultas e relevância esperada", "Mede recall, precision e ranking", "Justifica chunking e parâmetros de busca"]) ]),
    ("RAG", "Construir RAG rastreável, avaliar seus componentes e evoluir para padrões avançados e agentic RAG.",
     ["Pipeline RAG e respostas com citações", "Reranking, query rewriting e advanced RAG", "Avaliação de retrieval, groundedness e agentic RAG"],
     [("Implementar RAG com fontes verificáveis", 5, ["Conecta ingestão, retrieval e geração", "Preserva documento, trecho e página", "Distingue fonte, inferência e recomendação"]), ("Avaliar e aprimorar sistemas RAG", 5, ["Separa falhas de retrieval e geração", "Mede relevância e groundedness", "Justifica reranking ou agentic RAG"]) ]),
    ("MCP e ferramentas", "Integrar modelos a ferramentas por contratos explícitos, permissões mínimas e execução segura.",
     ["Tool calling, schemas e validação", "Protocolo MCP: recursos, prompts e ferramentas", "Permissões, idempotência, timeout e auditoria"],
     [("Implementar ferramentas seguras para LLMs", 4, ["Define schema estrito de entrada e saída", "Aplica autorização e idempotência", "Trata erros e timeouts sem ação duplicada"]), ("Projetar integração MCP", 5, ["Distingue recursos, prompts e tools", "Delimita trust boundaries", "Audita chamadas e resultados"]) ]),
    ("Agentes", "Evoluir de tool calling para agentes individuais com estado, contexto, limites e supervisão humana.",
     ["Estado, contexto, memória e ciclo do agente", "Planejamento, ferramentas e workflows determinísticos", "Human-in-the-loop e avaliação de agentes"],
     [("Implementar um agente individual controlado", 4, ["Modela estado e transições", "Limita ferramentas, iterações e orçamento", "Exige aprovação para ações críticas"]), ("Escolher entre agente e workflow", 5, ["Explicita grau necessário de autonomia", "Compara fluxo determinístico e decisão do modelo", "Justifica limites e fallback"]) ]),
    ("Sistemas Multiagentes", "Projetar colaboração entre agentes com papéis, handoffs, coordenação e síntese verificável.",
     ["Papéis, especialização e protocolos de handoff", "Orquestração, DAGs, filas e estado compartilhado", "Conflitos, consenso e avaliação multiagente"],
     [("Orquestrar sistemas multiagentes", 5, ["Define responsabilidades sem sobreposição ambígua", "Implementa handoff e estado rastreável", "Controla concorrência, retries e falhas parciais"]), ("Avaliar colaboração multiagente", 5, ["Mede contribuição por agente", "Detecta propagação de erro e consenso falso", "Compara com baseline de agente único"]) ]),
    ("IA Multimodal", "Projetar sistemas que integrem texto, imagem, áudio e documentos com avaliação por modalidade.",
     ["Representações e modelos multimodais", "Visão, áudio, OCR e documentos", "Pipelines multimodais e avaliação"],
     [("Implementar pipeline multimodal", 4, ["Normaliza entradas por modalidade", "Preserva proveniência dos artefatos", "Trata formatos, tamanho e falhas"]), ("Avaliar sistemas multimodais", 5, ["Define critérios por modalidade", "Analisa desalinhamento entre modalidades", "Justifica modelo, custo e latência"]) ]),
    ("Dados para IA", "Projetar dados confiáveis, versionados e governados para treinamento, recuperação e avaliação.",
     ["Aquisição, contratos e qualidade de dados", "Pipelines, feature engineering e versionamento", "Rotulagem, linhagem, privacidade e datasets de avaliação"],
     [("Construir pipelines de dados para IA", 4, ["Valida schema e qualidade", "Versiona dados e transformações", "Previne vazamento entre conjuntos"]), ("Governar dados de sistemas inteligentes", 5, ["Registra origem e consentimento", "Aplica retenção e minimização", "Justifica qualidade e adequação do dataset"]) ]),
    ("Fine-tuning", "Decidir, preparar e avaliar adaptações de modelos sem confundir ajuste com recuperação ou prompting.",
     ["Quando usar prompting, RAG ou fine-tuning", "Preparação de dados e métodos de adaptação", "Treinamento, avaliação, custo e regressão"],
     [("Planejar fine-tuning responsável", 5, ["Demonstra a lacuna do baseline", "Prepara dados representativos e licenciados", "Define avaliação e critério de parada"]), ("Executar e analisar adaptação de modelos", 4, ["Configura treinamento reproduzível", "Compara modelo base e ajustado", "Detecta regressões e memorização indesejada"]) ]),
    ("Avaliação de sistemas de IA", "Criar avaliações reproduzíveis para qualidade, segurança, custo e comportamento ponta a ponta.",
     ["Datasets, rubricas, graders e baselines", "Avaliação offline, online e testes adversariais", "Regressão, análise de erro e decisão de release"],
     [("Construir uma suíte de avaliação de IA", 5, ["Define casos representativos e edge cases", "Combina métricas e revisão humana", "Versiona dados, prompts, modelos e resultados"]), ("Tomar decisões com evidência de avaliação", 5, ["Segmenta falhas por causa", "Compara alternativas com incerteza", "Bloqueia release abaixo dos critérios"]) ]),
    ("Arquitetura de Sistemas Inteligentes", "Decompor sistemas de IA em componentes coesos, interfaces explícitas e modos de falha controlados.",
     ["Requisitos funcionais e atributos de qualidade", "Arquitetura modular, eventos, filas e armazenamento", "Resiliência, fallback e decisões arquiteturais"],
     [("Projetar arquitetura de sistema inteligente", 5, ["Produz diagrama, contratos e fluxos", "Mapeia dependências e modos de falha", "Relaciona decisões a atributos de qualidade"]), ("Defender decisões arquiteturais", 6, ["Compara alternativas e trade-offs", "Explica limites operacionais", "Comunica a arquitetura para públicos técnicos"]) ]),
    ("Segurança e Governança", "Aplicar segurança por design, governança, privacidade e supervisão humana em todo o ciclo.",
     ["Threat modeling, prompt injection e tool poisoning", "Identidade, autorização, segredos e isolamento", "Governança, risco, privacidade e uso responsável"],
     [("Proteger aplicações de IA", 5, ["Modela ameaças e trust boundaries", "Testa ataques e abuso de ferramentas", "Aplica menor privilégio e defesa em profundidade"]), ("Governar riscos de IA", 5, ["Classifica impacto e risco", "Define controles, responsáveis e auditoria", "Documenta risco residual e decisão humana"]) ]),
    ("Engenharia de Produção", "Transformar protótipos de IA em serviços confiáveis, observáveis e operáveis.",
     ["APIs, streaming, filas e concorrência", "Resiliência, rate limit, cache e custos", "Logs, métricas, traces, SLOs e incidentes"],
     [("Implementar serviços de IA confiáveis", 4, ["Define contratos e tratamento de erros", "Implementa retry, timeout e circuit breaker", "Controla concorrência e custo"]), ("Operar sistemas inteligentes", 5, ["Instrumenta logs, métricas e traces", "Define SLOs e alertas acionáveis", "Conduz diagnóstico e resposta a incidentes"]) ]),
    ("MLOps / LLMOps / AIOps", "Gerenciar o ciclo de vida de dados, modelos, prompts e avaliações com rastreabilidade operacional.",
     ["Tracking, registro e versionamento de artefatos", "Pipelines de treino, avaliação e promoção", "Drift, observabilidade de LLMs e automação operacional"],
     [("Implementar ciclo MLOps e LLMOps", 5, ["Versiona dados, código, modelo e prompt", "Automatiza gates de avaliação", "Promove e reverte artefatos com rastreabilidade"]), ("Aplicar AIOps com controle humano", 5, ["Correlaciona sinais operacionais", "Automatiza somente ações delimitadas", "Avalia falsos positivos e impacto operacional"]) ]),
    ("Cloud, Containers, CI/CD e Deploy", "Empacotar, testar e implantar serviços de IA de modo reproduzível e seguro.",
     ["Containers, imagens e configuração por ambiente", "Cloud, compute, storage, rede e identidade", "CI/CD, infraestrutura, deploy e rollback"],
     [("Containerizar e implantar aplicações de IA", 4, ["Produz imagem mínima e reproduzível", "Externaliza configuração e segredos", "Valida saúde, recursos e dependências"]), ("Projetar entrega contínua segura", 5, ["Automatiza testes e avaliações", "Aplica promoção entre ambientes", "Executa rollback e registra mudanças"]) ]),
    ("Arquitetura Enterprise AI-First", "Integrar capacidades de IA à arquitetura corporativa, aos dados e à governança sem criar silos.",
     ["Estratégia AI-first e portfólio de casos de uso", "Plataforma de IA, integração e arquitetura corporativa", "FinOps, governança federada e gestão de mudança"],
     [("Desenhar arquitetura enterprise AI-first", 5, ["Prioriza casos por valor, risco e viabilidade", "Define capacidades compartilhadas e domínios", "Integra identidade, dados, observabilidade e governança"]), ("Conduzir decisões enterprise de IA", 6, ["Compara build, buy e modelos híbridos", "Quantifica custo total e risco", "Explica roadmap e trade-offs a executivos e engenharia"]) ]),
    ("Capstone — Sensei AI Enterprise", "Integrar currículo em um sistema empresarial de IA que resolva um problema real e seja demonstrável.",
     ["Descoberta, requisitos e arquitetura do capstone", "Implementação incremental e validação ponta a ponta", "Operação, documentação e apresentação executiva"],
     [("Entregar o Sensei AI Enterprise", 6, ["Integra dados, IA, segurança e operação", "Demonstra testes, avaliações e observabilidade", "Entrega documentação reproduzível e limites conhecidos"]), ("Validar valor e prontidão empresarial", 5, ["Liga métricas técnicas ao resultado esperado", "Executa testes de falha e recuperação", "Apresenta riscos, custos e próximos passos"]) ]),
    ("Defesa Técnica e Capacidade de Ensinar", "Demonstrar autoria, defender decisões e ensinar o sistema construído sem delegar o raciocínio à IA.",
     ["Preparação da defesa e portfólio de evidências", "Arguição técnica, debugging ao vivo e trade-offs", "Didática, mentoria e aula demonstrativa"],
     [("Defender tecnicamente o sistema", 6, ["Explica decisões sem assistência da IA", "Responde a cenários de falha e alternativas", "Demonstra autoria e domínio do código"]), ("Ensinar engenharia de sistemas inteligentes", 6, ["Estrutura explicação progressiva e correta", "Adapta exemplos ao público", "Avalia compreensão e corrige concepções equivocadas"]) ]),
]


def seed_curriculum(apps, schema_editor):
    Formation = apps.get_model("library", "SenseiFormation")
    Module = apps.get_model("library", "SenseiFormationModule")
    Unit = apps.get_model("library", "SenseiStudyUnit")
    Competency = apps.get_model("library", "SenseiCompetency")
    formation = Formation.objects.get(slug=SLUG)

    for module_order, (title, objective, units, competencies) in enumerate(CURRICULUM):
        module, _ = Module.objects.update_or_create(
            formation=formation, order=module_order,
            defaults={"title": title, "description": objective},
        )
        for unit_order, unit_title in enumerate(units):
            Unit.objects.update_or_create(
                module=module, order=unit_order,
                defaults={"title": unit_title, "objective": f"Compreender e aplicar {unit_title.lower()} no contexto de sistemas inteligentes.", "status": "ACTIVE", "reference_links": []},
            )
        for competency_order, (competency_title, level, criteria) in enumerate(competencies):
            Competency.objects.update_or_create(
                formation=formation, module=module, order=competency_order,
                defaults={"title": competency_title, "description": objective, "expected_level": level, "mastery_criteria": criteria},
            )


class Migration(migrations.Migration):
    dependencies = [("library", "0011_seed_sensei_ai_engineering_formation")]
    operations = [migrations.RunPython(seed_curriculum, migrations.RunPython.noop)]
