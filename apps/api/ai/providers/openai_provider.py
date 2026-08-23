import logging

from openai import OpenAI
from django.conf import settings


logger = logging.getLogger("ai")


class OpenAIProvider:
    def __init__(self):
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não está configurada no ambiente.")

        self.model = getattr(settings, "OPENAI_AI_MODEL", "gpt-4.1-mini")
        self.client = OpenAI(api_key=api_key)

    def chat(self, messages):
        try:
            logger.info(
                "OpenAI chat iniciado: model=%s messages=%s",
                self.model,
                len(messages),
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )

            content = response.choices[0].message.content
            logger.info("OpenAI chat concluído com sucesso: model=%s", self.model)
            return content

        except Exception as exc:
            # Nunca registrar a API key. O objetivo é revelar no Render apenas
            # o tipo e a mensagem do erro retornado pelo provider.
            logger.exception(
                "Falha no OpenAI chat: type=%s message=%s model=%s",
                type(exc).__name__,
                str(exc),
                self.model,
            )
            raise
