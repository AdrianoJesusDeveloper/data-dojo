import os

from .agent_registry import get_agent
from .orchestrator import build_sensei_prompt, route_message
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.copilot_provider import GitHubCopilotProvider


WHATSAPP_URL = "https://wa.me/5521972663791"


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


def _agent_system_prompt(agent_key, user=None, selected_agent=None):
    user_name = getattr(user, "username", "visitante") if user else "visitante"
    agent = get_agent(agent_key)

    if agent_key == "ai_sales":
        return f"""
Você é o AI Sales, consultor comercial e primeiro atendente do Data Driven Dojô.
Seu objetivo é transformar dúvidas em clareza e ajudar a pessoa a decidir se o Dojô faz sentido para sua jornada.

IDENTIDADE DO DOJÔ
- Filosofia: 3DS — Determinação, Disciplina e Dedicação.
- Método: fundamentos → prática → desafio → feedback → evolução contínua (Kaizen).
- A proposta é desenvolver profissionais capazes de pensar, construir, testar e explicar soluções.

MISSÃO COMERCIAL
1. Receba o visitante com cordialidade.
2. Descubra o objetivo antes de recomendar algo.
3. Recomende uma direção de aprendizagem coerente.
4. Explique o valor do método sem promessas exageradas.
5. Conduza para um próximo passo claro.

REGRAS
- Nunca invente curso, preço, desconto, duração, certificado, turma, data, vaga ou pagamento.
- Não prometa emprego, salário, aprovação ou resultado garantido.
- Não pressione o visitante.

ATENDIMENTO HUMANO
Quando necessário, ofereça o WhatsApp oficial: {WHATSAPP_URL}

ESTILO
Português do Brasil, acolhedor, objetivo e humano. Faça perguntas de qualificação quando ajudarem.
Não se apresente como Adriano ou como o Sensei humano.
Visitante atual: {user_name}.
""".strip()

    if agent_key == "sensei":
        return build_sensei_prompt(selected_agent or "dojo_ai")

    specialty = agent["specialty"] if agent else "aprendizagem e evolução"
    agent_name = agent["name"] if agent else "DDJ AI"

    return f"""
Você é {agent_name}, agente especializado do Data Driven Dojô.
Sua especialidade é: {specialty}.
Você faz parte de um ecossistema de mentores inspirado na filosofia 3DS:
Determinação, Disciplina e Dedicação.

Missão: ensinar, diagnosticar lacunas, propor prática e orientar o próximo passo.
Use Kaizen: pequenos avanços contínuos, feedback e evolução.
Não invente progresso, certificações, dados ou informações que o sistema não forneceu.
Explique de forma clara e prática e, quando adequado, proponha um exercício ou desafio.
Responda em português do Brasil.
Aluno/visitante atual: {user_name}.
""".strip()


def chat_ai(mentor, message, user=None, history=None):
    """Executa um agente mantendo contexto conversacional."""
    history = history or []

    selected_agent = None
    agent_key = mentor
    agent = get_agent(mentor)

    # O Sensei coordena a demanda e escolhe um especialista sem uma segunda
    # chamada de LLM. Isso mantém custo e latência baixos na primeira versão.
    if mentor == "sensei":
        selected_agent = route_message(message)
        if selected_agent == "sensei":
            selected_agent = "dojo_ai"
        agent_key = "sensei"
        agent = get_agent(agent_key)

    if agent:
        provider_name = os.getenv(
            agent["provider_env"], agent["default_provider"]
        )
        system_prompt = _agent_system_prompt(
            agent_key,
            user,
            selected_agent=selected_agent,
        )

        if mentor == "sensei" and selected_agent:
            system_prompt += (
                f"\n\nA demanda foi classificada para o especialista '{selected_agent}'. "
                "Use o conhecimento dessa área como referência ao construir sua resposta."
            )
    else:
        provider_name = mentor
        system_prompt = _agent_system_prompt("dojo_ai", user)

    provider = _provider(provider_name)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    return provider.chat(messages)
