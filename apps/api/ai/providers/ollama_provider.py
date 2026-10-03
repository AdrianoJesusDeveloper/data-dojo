import logging
import os
from urllib.parse import urlparse

import requests


logger = logging.getLogger("ai")


def _provider_error(code):
    from ai.services import AIProviderError

    return AIProviderError(code, "ollama")


def _local_base_url():
    base_url = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise _provider_error("authentication")

    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise _provider_error("invalid_request")

    return base_url


class OllamaProvider:
    """Provider local para Ollama usando a API nativa /api/chat."""

    def chat(self, messages, response_schema=None):
        base_url = _local_base_url()
        model = os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip()

        if not model:
            raise _provider_error("authentication")

        payload = {
            "model": model,
            "messages": list(messages),
            "stream": False,
        }

        if response_schema is not None:
            payload["format"] = (
                "json"
                if response_schema == {"type": "json_object"}
                else response_schema
            )
            payload["options"] = {"temperature": 0}

        logger.info(
            "Ollama chat iniciado: model=%s messages=%s structured=%s",
            model,
            len(messages),
            response_schema is not None,
        )

        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            logger.warning("Ollama chat falhou: code=timeout model=%s", model)
            raise _provider_error("timeout") from exc
        except requests.ConnectionError as exc:
            logger.warning("Ollama chat falhou: code=unavailable model=%s", model)
            raise _provider_error("unavailable") from exc
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 413:
                code = "payload_too_large"
            elif status_code == 429:
                code = "rate_limit"
            elif status_code in {401, 403}:
                code = "authentication"
            elif status_code in {400, 404, 422}:
                code = "invalid_request"
            elif status_code is not None and status_code >= 500:
                code = "unavailable"
            else:
                code = "unknown"
            logger.warning(
                "Ollama chat falhou: code=%s status=%s model=%s",
                code,
                status_code,
                model,
            )
            raise _provider_error(code) from exc
        except requests.RequestException as exc:
            logger.warning("Ollama chat falhou: code=unknown model=%s", model)
            raise _provider_error("unknown") from exc

        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise _provider_error("invalid_response") from exc

        if not isinstance(content, str) or not content.strip():
            raise _provider_error("invalid_response")

        logger.info(
            "Ollama chat concluído: model=%s structured=%s",
            model,
            response_schema is not None,
        )
        return content
