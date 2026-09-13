from django.db import migrations


SLUG = "marketing-digital-performance-gestao-trafego-pago"


CURRICULUM = [
    ("Fundamentos de Marketing e Tráfego", "Relacionar marketing, aquisição e tráfego ao valor entregue ao cliente e ao negócio.",
     [("Marketing, aquisição e geração de valor", "Explicar como marketing e aquisição conectam problemas reais a ofertas."), ("Tráfego orgânico, pago e jornada do cliente", "Comparar canais e mapear sua função na jornada."), ("Objetivos, público, oferta e papel do gestor", "Delimitar objetivos, público e responsabilidades profissionais.")],
     [("Diagnosticar fundamentos de aquisição para um negócio", 4, ["Relaciona oferta, público, canal e jornada", "Distingue tráfego orgânico e pago", "Explicita limites do papel profissional"]), ("Justificar objetivos de marketing conectados ao negócio", 5, ["Traduz objetivo de negócio em objetivo de marketing", "Identifica dados ausentes", "Defende prioridades e restrições"])]),
    ("Fundamentos da Gestão de Tráfego", "Compreender os componentes duráveis de sistemas de mídia paga e seu aprendizado algorítmico.",
     [("Campanhas, grupos e anúncios", "Estruturar hierarquias de campanha sem depender de uma interface específica."), ("Leilão, orçamento e segmentação", "Explicar como disputa, verba e público condicionam a entrega."), ("Criativos, algoritmos e aprendizado", "Analisar a interação entre sinais, criativos e aprendizado das plataformas.")],
     [("Estruturar uma campanha de mídia paga", 4, ["Separa decisões de campanha, grupo e anúncio", "Relaciona orçamento e segmentação", "Documenta hipóteses"]), ("Explicar e diagnosticar a entrega algorítmica", 4, ["Explica leilão e aprendizado", "Identifica sinais insuficientes", "Evita alterações sem hipótese"])]),
    ("Estratégia, Oferta e Funil", "Alinhar problema, proposta de valor, público, jornada, funil e conversão.",
     [("Problema, proposta de valor e oferta", "Avaliar se a oferta responde a um problema relevante."), ("ICP, persona, jornada e funil", "Estruturar hipóteses de público e progressão de decisão."), ("Landing page, conversão e alinhamento com o negócio", "Diagnosticar a continuidade entre mídia, página e resultado.")],
     [("Projetar um funil coerente com oferta e público", 5, ["Explicita problema e proposta de valor", "Relaciona etapas da jornada", "Define conversões observáveis"]), ("Diagnosticar desalinhamentos entre mídia e conversão", 4, ["Separa falhas de mensagem, público e página", "Formula hipóteses testáveis", "Prioriza correções"])]),
    ("Criativos e Copy para Performance", "Tratar comunicação e criativos como hipóteses de performance passíveis de teste.",
     [("Ângulos, hooks e ofertas", "Construir variações de comunicação ancoradas no problema e na oferta."), ("Formatos e biblioteca de referências", "Organizar referências legítimas e selecionar formatos pelo contexto."), ("Testes criativos e comunicação de conversão", "Planejar testes que isolem hipóteses criativas.")],
     [("Avaliar e formular hipóteses criativas", 5, ["Relaciona ângulo, hook, formato e oferta", "Distingue referência de cópia", "Define critério de avaliação"]), ("Planejar testes de criativos para performance", 4, ["Controla variáveis relevantes", "Documenta versões", "Interpreta resultados sem conclusão precipitada"])]),
    ("Meta Ads", "Estruturar e analisar aquisição no ecossistema Meta por conceitos duráveis.",
     [("Objetivos, estrutura e públicos no Meta", "Relacionar objetivo, estrutura e público à hipótese de aquisição."), ("Posicionamentos, criativos e orçamento", "Planejar entrega considerando formato, inventário e verba."), ("Campanhas e leitura de resultados", "Ler resultados conectando sinais de mídia e negócio.")],
     [("Estruturar e justificar uma campanha de aquisição no Meta Ads", 5, ["Justifica objetivo, público, criativo e orçamento", "Define métricas de mídia e negócio", "Explicita riscos"]), ("Diagnosticar performance de campanhas Meta", 4, ["Segmenta causas prováveis", "Compara períodos adequadamente", "Propõe próximo teste"])]),
    ("Google Ads", "Planejar aquisição orientada à intenção e avaliar suas modalidades.",
     [("Search, intenção e palavras-chave", "Modelar intenção de busca e sua relação com a oferta."), ("Estrutura, anúncios, lances e conversões", "Estruturar campanhas de busca com mensuração coerente."), ("Modalidades e análise no Google Ads", "Selecionar modalidades e analisar resultados conforme objetivo.")],
     [("Estruturar campanhas de busca orientadas à intenção", 5, ["Agrupa intenções coerentemente", "Alinha anúncio e destino", "Justifica lances e conversões"]), ("Avaliar modalidades e performance no Google Ads", 4, ["Compara modalidades pelo caso", "Diagnostica termos e conversões", "Evita otimização por métrica isolada"])]),
    ("TikTok Ads e Novas Fontes de Aquisição", "Compreender linguagem de plataforma e avaliar novos canais com evidências.",
     [("Linguagem, público e criativos no TikTok", "Adaptar hipóteses criativas ao contexto de consumo da plataforma."), ("Campanhas e mensuração no TikTok Ads", "Planejar campanha e sinais de mensuração."), ("Avaliação de novos canais de aquisição", "Criar critérios para testar canais emergentes sem seguir modismos.")],
     [("Planejar aquisição coerente com a linguagem do TikTok", 4, ["Relaciona criativo, público e objetivo", "Define mensuração", "Reconhece limites de atribuição"]), ("Avaliar novos canais de aquisição", 5, ["Define hipótese e critério de entrada", "Limita investimento experimental", "Compara valor incremental"])]),
    ("LinkedIn Ads e Marketing B2B", "Avaliar aquisição B2B considerando segmentação profissional, qualidade e economia.",
     [("Segmentação profissional e contexto B2B", "Mapear contas, papéis e problemas em ciclos B2B."), ("Geração e qualificação de leads", "Definir qualidade do lead e continuidade comercial."), ("Custo, estratégia e análise econômica", "Avaliar custo de aquisição diante do valor e ciclo de venda.")],
     [("Estruturar uma estratégia de aquisição B2B no LinkedIn", 5, ["Justifica segmentação profissional", "Define qualidade de lead", "Conecta marketing e vendas"]), ("Avaliar economicamente campanhas B2B", 5, ["Relaciona custo, ciclo e valor esperado", "Analisa qualidade além do volume", "Defende continuidade ou interrupção"])]),
    ("Métricas e Economia de Aquisição", "Diagnosticar performance conectando métricas de mídia à economia do negócio.",
     [("Entrega e resposta: impressões, alcance, frequência, CPM, CPC e CTR", "Interpretar conjuntamente entrega, exposição e resposta."), ("Conversão: CPL, CPA, CVR e ROAS", "Diagnosticar custo e eficiência de conversão sem isolar indicadores."), ("Negócio: CAC, LTV, margem, ticket, break-even, receita e lucro", "Conectar aquisição à sustentabilidade financeira.")],
     [("Interpretar métricas de aquisição como sistema", 5, ["Relaciona entrega, clique e conversão", "Detecta denominadores e comparações inválidas", "Formula diagnóstico"]), ("Conectar mídia a resultado financeiro", 5, ["Calcula e interpreta CAC, LTV, margem e break-even", "Distingue receita de lucro", "Justifica limites de investimento"])]),
    ("Tracking, Mensuração e Qualidade dos Dados", "Projetar e validar mensuração confiável com privacidade e consentimento.",
     [("Pixels, tags, eventos, conversões e UTMs", "Desenhar um plano de eventos e identificação de campanhas."), ("GA4, GTM e atribuição", "Compreender coleta, organização e limites de atribuição."), ("Privacidade, consentimento, discrepâncias e validação", "Avaliar qualidade e conformidade dos dados de marketing.")],
     [("Planejar e implementar mensuração de marketing", 4, ["Define eventos e conversões", "Padroniza UTMs", "Documenta coleta e validação"]), ("Diagnosticar qualidade e discrepâncias de tracking", 4, ["Reconcilia fontes e definições", "Identifica perdas e duplicidades", "Respeita privacidade e consentimento"])]),
    ("Otimização de Campanhas", "Tomar decisões de otimização a partir de diagnósticos, hipóteses e evidências.",
     [("Diagnóstico e formulação de hipóteses", "Separar sintomas, causas prováveis e dados necessários."), ("Orçamento, públicos, criativos, frequência e funil", "Avaliar alavancas de otimização de modo integrado."), ("Escala, redução e quando não mexer", "Definir condições para agir, esperar, escalar ou reduzir.")],
     [("Diagnosticar campanhas e priorizar hipóteses", 5, ["Separa sintomas de causas", "Solicita dados faltantes", "Prioriza por impacto e incerteza"]), ("Justificar decisões de otimização e escala", 5, ["Define condições de intervenção", "Considera aprendizado e volatilidade", "Explica quando não alterar"])]),
    ("Experimentação e Dados para Marketing", "Aplicar o método Data Driven Dojô para experimentar, analisar e decidir sob incerteza.",
     [("Hipóteses, variáveis, vieses e testes A/B", "Planejar experimentos que respondam perguntas claras."), ("Amostra, correlação e causalidade", "Interpretar evidência com limites estatísticos aplicados."), ("Dashboards, análise exploratória e decisão", "Construir leituras que apoiem decisões em vez de apenas exibir números.")],
     [("Planejar experimentos de marketing", 5, ["Formula hipótese falsificável", "Controla variáveis e vieses", "Define métrica e critério de decisão"]), ("Analisar dados de marketing criticamente", 5, ["Distingue correlação de causalidade", "Explicita limitações de amostra", "Transforma achados em decisão defensável"])]),
    ("Estratégias por Modelo de Negócio", "Adaptar estratégia de aquisição ao modelo econômico e ao ciclo do cliente.",
     [("Negócio local, serviços e geração de leads", "Comparar objetivos, restrições e mensuração nesses cenários."), ("E-commerce e infoprodutos", "Relacionar catálogo, oferta, margem, recorrência e funil."), ("B2B e escolha de estratégia pelo modelo econômico", "Projetar aquisição considerando ciclo, ticket e capacidade comercial.")],
     [("Projetar estratégias para diferentes modelos de negócio", 5, ["Adapta canal, funil e KPI", "Considera ciclo, ticket e margem", "Justifica diferenças entre cenários"]), ("Avaliar adequação econômica de uma estratégia", 5, ["Modela restrições", "Conecta aquisição e capacidade operacional", "Recomenda com incerteza explícita"])]),
    ("Operação Profissional de Tráfego", "Organizar uma operação responsável, documentada e comunicável.",
     [("Briefing, onboarding e acessos", "Coletar contexto e organizar acessos com segurança e responsabilidade."), ("Rotina, relatórios, reuniões e comunicação", "Criar cadência operacional orientada a decisões."), ("Processos, contingências e gestão de expectativas", "Documentar operação, riscos, responsabilidades e respostas.")],
     [("Estruturar uma operação profissional de tráfego", 5, ["Produz briefing e onboarding", "Organiza acessos e processos", "Define rotinas e responsáveis"]), ("Comunicar performance, riscos e expectativas", 5, ["Apresenta resultados com contexto", "Documenta contingências", "Alinha expectativas eticamente"])]),
    ("Prospecção, Vendas e Operação de Agência", "Construir uma operação comercial ética, sustentável e coerente com a entrega.",
     [("Posicionamento, aquisição de clientes e prospecção", "Definir posicionamento e abordagem comercial responsável."), ("Diagnóstico, reunião, proposta, precificação e escopo", "Transformar necessidades reais em proposta delimitada."), ("Retenção, relacionamento, crescimento e ética", "Gerir valor, limites e continuidade da relação.")],
     [("Conduzir diagnóstico comercial e elaborar proposta", 5, ["Investiga contexto antes de ofertar", "Define escopo e exclusões", "Justifica precificação e entregáveis"]), ("Estruturar crescimento ético de uma operação de agência", 5, ["Relaciona capacidade e aquisição", "Define retenção por valor", "Evita promessas enganosas"])]),
    ("IA e Automação para Marketing de Performance", "Aplicar IA e automação ao trabalho mecânico sem delegar julgamento e responsabilidade.",
     [("IA para pesquisa, análise e hipóteses", "Usar IA como apoio verificável à investigação e ao diagnóstico."), ("IA para criativos, campanhas, relatórios e automação", "Automatizar tarefas delimitadas com revisão humana."), ("Agentes, riscos, validação humana e governança", "Projetar limites, auditoria e supervisão para automações."), ("Capstone: Operação Data Driven de Marketing de Performance", "Integrar negócio, estratégia, tracking, campanhas, dados, otimização, relatório e defesa técnica.")],
     [("Aplicar IA ao marketing com supervisão humana", 5, ["Delimita trabalho mecânico e julgamento", "Valida saídas e fontes", "Documenta riscos e intervenções"]), ("Defender uma operação Data Driven de marketing de performance", 6, ["Integra objetivo, oferta, canais, tracking, campanhas e KPIs", "Diagnostica e otimiza com evidências", "Apresenta e defende decisões, riscos e limites"])]),
]


def seed_marketing_formation(apps, schema_editor):
    Formation = apps.get_model("library", "SenseiFormation")
    Module = apps.get_model("library", "SenseiFormationModule")
    Unit = apps.get_model("library", "SenseiStudyUnit")
    Competency = apps.get_model("library", "SenseiCompetency")
    Plan = apps.get_model("library", "SenseiUnitStudyPlan")
    Gap = apps.get_model("library", "SenseiUnitSourceGap")

    formation, _ = Formation.objects.update_or_create(
        slug=SLUG,
        defaults={
            "title": "Marketing Digital, Performance e Gestão de Tráfego Pago",
            "description": "Formação autoral Data Driven Dojô para planejar, executar, analisar e defender operações de marketing de performance.",
            "objective": "Desenvolver competência técnica, analítica e profissional para conectar aquisição, dados e decisões a resultados sustentáveis de negócio.",
            "status": "ACTIVE",
            "level": "Do fundamento à defesa técnica",
            "created_by": None,
        },
    )
    for module_order, (title, description, units, competencies) in enumerate(CURRICULUM):
        module, _ = Module.objects.update_or_create(formation=formation, order=module_order, defaults={"title": title, "description": description})
        module_competencies = []
        for competency_order, (competency_title, expected_level, criteria) in enumerate(competencies):
            competency, _ = Competency.objects.update_or_create(
                formation=formation, module=module, order=competency_order,
                defaults={"title": competency_title, "description": description, "expected_level": expected_level, "mastery_criteria": criteria},
            )
            module_competencies.append(competency)
        for unit_order, (unit_title, unit_objective) in enumerate(units):
            unit, _ = Unit.objects.update_or_create(
                module=module, order=unit_order,
                defaults={"title": unit_title, "objective": unit_objective, "status": "ACTIVE", "reference_links": []},
            )
            plan, _ = Plan.objects.update_or_create(
                unit=unit,
                defaults={
                    "learning_objectives": [unit_objective],
                    "practices": ["Analisar um cenário, explicitar dados ausentes e formular uma hipótese.", "Propor uma decisão, definir como validá-la e justificar seus limites."],
                    "expected_evidence": ["Análise autoral com hipótese, dados, decisão e justificativa.", "Artefato prático ou defesa técnica submetida ao fluxo de validação."],
                    "completion_criteria": ["Explica os conceitos com palavras próprias.", "Aplica os conceitos a um cenário e reconhece incertezas.", "Não confunde conclusão de estudo com competência demonstrada."],
                    "guidance": "Compreender → raciocinar → estruturar hipóteses → consultar IA quando apropriado → revisar → validar → implementar → explicar.",
                },
            )
            plan.related_competencies.set(module_competencies)
            Gap.objects.update_or_create(
                unit=unit,
                defaults={"status": "OPEN", "reason": "NEEDS_SOURCE: fonte adequada ainda não foi curada para esta unidade.", "requirements": ["Priorizar documentação oficial para detalhes operacionais atuais e fontes públicas legítimas e verificáveis."], "notes": "Nenhuma fonte foi associada automaticamente.", "created_by": None, "resolved_at": None, "resolved_by": None},
            )


def remove_marketing_formation(apps, schema_editor):
    apps.get_model("library", "SenseiFormation").objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [("library", "0021_senseilearningattempt")]
    operations = [migrations.RunPython(seed_marketing_formation, remove_marketing_formation)]
