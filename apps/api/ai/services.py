from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider import GeminiProvider
from .providers.deepseek_provider import DeepSeekProvider



def chat_ai(mentor, message):

    if mentor == "chatgpt":
        provider = OpenAIProvider()

    elif mentor == "gemini":
        provider = GeminiProvider()

    elif mentor == "deepseek":
        provider = DeepSeekProvider()

    else:
        raise ValueError(
            "Mentor de IA não encontrado"
        )


    return provider.chat(message)