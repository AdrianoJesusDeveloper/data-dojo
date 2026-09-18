import logging
import os
import ssl

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from django.conf import settings

logger = logging.getLogger("ai")


def _provider_error(code):
    # Imported lazily so adapters remain directly importable while services.py
    # continues to own the normalized provider error abstraction.
    from ai.services import AIProviderError

    return AIProviderError(code, "openai")


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
            raise _provider_error("authentication")

        self.model = getattr(settings, "OPENAI_AI_MODEL", "gpt-4.1-mini")
        self.client = OpenAI(api_key=api_key, http_client=_secure_http_client())

    def chat(self, messages, response_schema=None):
        try:
            logger.info(
                "OpenAI chat iniciado: model=%s messages=%s",
                self.model,
                len(messages),
            )

            request = {"model": self.model, "messages": messages}
            if response_schema is not None:
                request["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_response",
                        "strict": True,
                        "schema": response_schema,
                    },
                }
            response = self.client.chat.completions.create(**request)

            choices = getattr(response, "choices", None)
            if not choices:
                raise _provider_error("invalid_response")
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if not isinstance(content, str) or not content.strip():
                raise _provider_error("invalid_response")
            logger.info("OpenAI chat concluído com sucesso: model=%s", self.model)
            return content

        except APITimeoutError as exc:
            raise self._error("timeout", exc) from exc
        except RateLimitError as exc:
            raise self._error("rate_limit", exc) from exc
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise self._error("authentication", exc) from exc
        except (BadRequestError, NotFoundError, UnprocessableEntityError) as exc:
            raise self._error("invalid_request", exc) from exc
        except (InternalServerError, APIConnectionError) as exc:
            raise self._error("unavailable", exc) from exc
        except APIStatusError as exc:
            if exc.status_code == 413:
                code = "payload_too_large"
            elif exc.status_code >= 500:
                code = "unavailable"
            else:
                code = "unknown"
            raise self._error(code, exc) from exc

    def _error(self, code, exc):
        logger.warning(
            "OpenAI chat falhou: code=%s type=%s model=%s",
            code,
            type(exc).__name__,
            self.model,
        )
        return _provider_error(code)
