"""Orquestração leve do ecossistema de agentes do Data Driven Dojô.

Primeira versão: roteamento determinístico por intenção. Evita uma chamada
extra ao LLM apenas para descobrir qual especialista deve responder.
"""

ROUTES = {
    "ai_sales": ("vender", "vendas", "cliente", "lead", "produto", "preço", "comprar", "whatsapp"),
    "career": ("currículo", "cv", "vaga", "emprego", "carreira", "entrevista", "linkedin", "salário"),
    "data": ("python", "sql", "pandas", "dados", "data science", "estatística", "power bi", "analytics"),
    "cloud": ("aws", "azure", "gcp", "cloud", "lambda", "s3", "ec2", "docker", "arquitetura"),
    "ai_engineer": ("ia", "ai", "llm", "rag", "agente", "openai", "gemini", "prompt", "machine learning"),
    "marketing": ("marketing", "instagram", "funil", "conteúdo", "marca", "seo", "anúncio"),
    "youtube": ("youtube", "vídeo", "roteiro", "thumbnail", "canal", "inscrito"),
}


def route_message(message, default="dojo_ai"):
    """Retorna o agente especialista mais provável para a mensagem."""
    text = (message or "").strip().lower()
    if not text:
        return default

    scores = {}
    for agent, keywords in ROUTES.items():
        scores[agent] = sum(1 for keyword in keywords if keyword in text)

    agent, score = max(scores.items(), key=lambda item: item[1])
    return agent if score else default


def build_sensei_prompt(selected_agent):
    """Prompt de coordenação usado quando o usuário escolhe o Sensei."""
    return f"""
Você é o Sensei AI, coordenador estratégico do Data Driven Dojô.
Sua função é entender o objetivo do aluno, encaminhar mentalmente a demanda
para o especialista mais adequado e entregar uma resposta organizada.

Especialista selecionado para esta demanda: {selected_agent}.

Regras:
- Pense estrategicamente antes de responder.
- Não invente informações.
- Priorize qualidade, clareza e ação prática.
- Quando a demanda envolver várias áreas, explique a prioridade e os próximos passos.
- Use a filosofia 3DS: Determinação, Disciplina e Dedicação.
- Use Kaizen: pequenos avanços contínuos com feedback.
- Responda em português do Brasil.
""".strip()
