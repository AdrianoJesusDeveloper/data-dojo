import os
import logging

import requests

logger = logging.getLogger("ai")


def _gemini_schema(value):
    """Convert standard JSON Schema to Gemini's supported Schema subset."""
    if isinstance(value, list):
        return [_gemini_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    converted = {}
    for key, item in value.items():
        if key == "additionalProperties":
            continue
        if key == "type" and isinstance(item, str):
            converted[key] = item.upper()
        elif key == "type" and isinstance(item, list):
            concrete = [value for value in item if value != "null"]
            converted[key] = concrete[0].upper()
            if "null" in item:
                converted["nullable"] = True
        else:
            converted[key] = _gemini_schema(item)
    return converted


def _provider_error(code):
    from ai.services import AIProviderError

    return AIProviderError(code, "gemini")


class GeminiProvider:
    """Provider Gemini usando a API REST oficial configurada no backend."""

    def chat(self, messages, response_schema=None):
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

        if not api_key:
            raise _provider_error("authentication")

        if os.name == "nt":
            try:
                import truststore

                truststore.inject_into_ssl()
            except ImportError:
                pass

        contents = []
        for item in messages:
            if item["role"] == "system":
                continue
            contents.append({
                "role": "model" if item["role"] == "assistant" else "user",
                "parts": [{"text": item["content"]}],
            })

        system_instruction = next(
            (item["content"] for item in messages if item["role"] == "system"),
            None,
        )

        payload = {"contents": contents}
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        if response_schema is not None:
            payload["generationConfig"] = {
                "responseMimeType": "application/json",
                "responseSchema": _gemini_schema(response_schema),
            }

        try:
            logger.info(
                "Gemini chat iniciado: model=%s messages=%s structured=%s",
                model,
                len(messages),
                response_schema is not None,
            )
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": api_key},
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            logger.warning("Gemini chat falhou: code=timeout type=%s model=%s", type(exc).__name__, model)
            raise _provider_error("timeout") from exc
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code == 429:
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
                "Gemini chat falhou: code=%s type=%s status=%s model=%s",
                code,
                type(exc).__name__,
                status_code,
                model,
            )
            raise _provider_error(code) from exc
        except requests.ConnectionError as exc:
            logger.warning("Gemini chat falhou: code=unavailable type=%s model=%s", type(exc).__name__, model)
            raise _provider_error("unavailable") from exc
        except requests.RequestException as exc:
            logger.warning("Gemini chat falhou: code=unknown type=%s model=%s", type(exc).__name__, model)
            raise _provider_error("unknown") from exc

        try:
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise _provider_error("invalid_response") from exc
        if not isinstance(content, str) or not content.strip():
            raise _provider_error("invalid_response")
        logger.info("Gemini chat concluído: model=%s structured=%s", model, response_schema is not None)
        return content
