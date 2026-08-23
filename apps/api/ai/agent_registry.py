"""Registro central dos agentes do Data Driven Dojô.

A ideia foi inspirada no antigo DataDrivenDojoAI, mas o runtime fica no
backend Django atual. Assim, novos agentes podem ser adicionados sem criar
uma nova aplicação Django para cada especialidade.
"""

AGENT_REGISTRY = {
    "dojo_ai": {
        "name": "DDJ AI",
        "description": "Sensei de evolução e aprendizagem personalizada.",
        "provider_env": "DDJ_AI_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "mentoria geral, fundamentos e evolução contínua",
    },
    "sensei": {
        "name": "Sensei AI",
        "description": "Mentor estratégico e coordenador da jornada do aluno.",
        "provider_env": "SENSEI_AI_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "estratégia, planejamento, organização e priorização",
    },
    "data": {
        "name": "Data Sensei",
        "description": "Mentor de dados, analytics e ciência de dados.",
        "provider_env": "DATA_AI_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "Python, SQL, estatística, análise e Data Science",
    },
    "ai_engineer": {
        "name": "AI Engineer Sensei",
        "description": "Mentor de engenharia de IA e aplicações inteligentes.",
        "provider_env": "AI_ENGINEER_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "LLMs, APIs, agentes, RAG, avaliação e integração",
    },
    "cloud": {
        "name": "Cloud Sensei",
        "description": "Mentor de cloud computing e arquitetura.",
        "provider_env": "CLOUD_AI_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "AWS, arquitetura, segurança, deploy e custos",
    },
    "career": {
        "name": "Career Sensei",
        "description": "Mentor de carreira e posicionamento profissional.",
        "provider_env": "CAREER_AI_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "portfólio, currículo, entrevistas e estratégia profissional",
    },
    "marketing": {
        "name": "Marketing Sensei",
        "description": "Mentor de marketing, conteúdo e aquisição.",
        "provider_env": "MARKETING_AI_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "posicionamento, conteúdo, funil e aquisição",
    },
    "youtube": {
        "name": "YouTube Sensei",
        "description": "Mentor de conteúdo e crescimento no YouTube.",
        "provider_env": "YOUTUBE_AI_PROVIDER",
        "default_provider": "chatgpt",
        "public": False,
        "specialty": "roteiros, títulos, thumbnails, aulas e estratégia de canal",
    },
    "ai_sales": {
        "name": "AI Sales",
        "description": "Agente comercial para atendimento, qualificação e conversão.",
        "provider_env": "AI_SALES_PROVIDER",
        "default_provider": "chatgpt",
        "public": True,
        "specialty": "atendimento comercial, descoberta de necessidades e próximos passos",
    },
}


def get_agent(agent_key):
    return AGENT_REGISTRY.get(agent_key)


def public_agents():
    return [
        {"key": key, **config}
        for key, config in AGENT_REGISTRY.items()
        if config["public"]
    ]
