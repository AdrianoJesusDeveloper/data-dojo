import logging
import os
import ssl

import httpx
from openai import OpenAI
from django.conf import settings


logger = logging.getLogger("ai")


def _secure_http_client():
    """Usa a cadeia de certificados do Windows sem desativar TLS."""
    if os.name == "nt":
        try:
            import truststore

            context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            return httpx.Client(verify=context, timeout=90)
        except ImportError:
            logger.warning("truststore não instalado; usando certificados padrão do Python")
    return httpx.Client(timeout=90)


class OpenAIProvider:
    def __init__(self):
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não está configurada no ambiente.")

        self.model = getattr(settings, "OPENAI_AI_MODEL", "gpt-4.1-mini")
        self.client = OpenAI(api_key=api_key, http_client=_secure_http_client())

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
            logger.exception(
                "Falha no OpenAI chat: type=%s message=%s model=%s",
                type(exc).__name__,
                str(exc),
                self.model,
            )
            raise
