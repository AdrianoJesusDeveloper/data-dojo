from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.copilot_provider import GitHubCopilotProvider


AGENTS = {
    "dojo_ai": {
        "name": "DDJ AI",
        "description": "Sensei de evolução e aprendizagem personalizada do aluno.",
        "provider_env": "DDJ_AI_PROVIDER",
        "default_provider": "chatgpt",
    },
    "ai_sales": {
        "name": "AI Sales",
        "description": "Agente comercial para atendimento, recomendação e conversão de leads.",
        "provider_env": "AI_SALES_PROVIDER",
        "default_provider": "chatgpt",
    },
}


def _provider(name):
    providers = {
        "chatgpt": OpenAIProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "deepseek": DeepSeekProvider,
        "copilot": GitHubCopilotProvider,
    }
    try:
        return providers[name]()
    except KeyError as exc:
        raise ValueError("Provedor de IA não encontrado") from exc


def _agent_system_prompt(agent_key, user=None):
    user_name = getattr(user, "username", "aluno") if user else "aluno"

    if agent_key == "ai_sales":
        return (
            "Você é o AI Sales do Data Driven Dojô. "
            "Seu papel é atender visitantes e leads com clareza, entender objetivos, "
            "recomendar a trilha mais adequada, responder dúvidas comerciais e conduzir "
            "o próximo passo sem pressionar ou inventar preços, benefícios ou condições. "
            "Quando não souber algo, diga que precisa confirmar."
        )

    return (
        f"Você é o DDJ AI, o Sensei de evolução do Data Driven Dojô. "
        f"O aluno se chama {user_name}. Você deve ensinar em vez de apenas entregar respostas, "
        "diagnosticar lacunas, propor exercícios, incentivar prática e conectar o conteúdo "
        "à jornada do aluno. Priorize Python, SQL, dados, IA, engenharia de dados, cloud e lógica. "
        "Use a filosofia Kaizen: pequenos avanços contínuos, feedback e próximo desafio. "
        "Nunca finja conhecer progresso que não foi fornecido pelo sistema."
    )


def chat_ai(mentor, message, user=None, history=None):
    """Executa um agente ou provedor mantendo contexto conversacional."""
    history = history or []

    agent = AGENTS.get(mentor)
    if agent:
        provider_name = __import__("os").getenv(
            agent["provider_env"], agent["default_provider"]
        )
        system_prompt = _agent_system_prompt(mentor, user)
    else:
        provider_name = mentor
        system_prompt = _agent_system_prompt("dojo_ai", user)

    provider = _provider(provider_name)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    return provider.chat(messages)
