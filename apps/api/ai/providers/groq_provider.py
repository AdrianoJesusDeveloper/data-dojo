import logging
import os

import requests


logger = logging.getLogger(__name__)


def _provider_error(code):
    from ai.services import AIProviderError

    return AIProviderError(code, "groq")


class GroqProvider:
    def chat(self, messages, response_schema=None):
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

        if not api_key:
            raise _provider_error("authentication")

        base_messages = list(messages)
        max_attempts = 2 if response_schema is not None else 1

        for attempt in range(max_attempts):
            request_messages = list(base_messages)
            if attempt == 1:
                request_messages.append(
                    {
                        "role": "system",
                        "content": (
                            "A geração estruturada anterior não correspondeu ao JSON Schema. "
                            "Tente novamente obedecendo estritamente ao schema fornecido pelo provedor. "
                            "Inclua TODAS as propriedades obrigatórias, mesmo quando o valor correto "
                            "for uma lista vazia. Não acrescente propriedades extras e não envolva o "
                            "JSON em Markdown."
                        ),
                    }
                )

            payload = {
                "model": model,
                "messages": request_messages,
                "max_completion_tokens": 8192,
                "reasoning_effort": "low",
            }

            if response_schema is not None:
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "ddj_structured_response",
                        "strict": True,
                        "schema": response_schema,
                    },
                }

            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=90,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            except requests.Timeout as exc:
                raise _provider_error("timeout") from exc
            except requests.ConnectionError as exc:
                raise _provider_error("unavailable") from exc
            except requests.HTTPError as exc:
                response = exc.response
                status_code = response.status_code if response is not None else None

                if status_code == 429:
                    logger.warning(
                        "groq_rate_limit status=%s retry_after=%s "
                        "limit_requests=%s remaining_requests=%s reset_requests=%s "
                        "limit_tokens=%s remaining_tokens=%s reset_tokens=%s",
                        status_code,
                        response.headers.get("retry-after"),
                        response.headers.get("x-ratelimit-limit-requests"),
                        response.headers.get("x-ratelimit-remaining-requests"),
                        response.headers.get("x-ratelimit-reset-requests"),
                        response.headers.get("x-ratelimit-limit-tokens"),
                        response.headers.get("x-ratelimit-remaining-tokens"),
                        response.headers.get("x-ratelimit-reset-tokens"),
                    )
                    code = "rate_limit"
                elif status_code in {401, 403}:
                    code = "authentication"
                elif status_code in {400, 404, 422}:
                    error_code = None
                    try:
                        error_payload = response.json()
                        error_data = error_payload.get("error", {}) if isinstance(error_payload, dict) else {}
                        if isinstance(error_data, dict) and error_data.get("code") == "json_validate_failed":
                            error_code = "json_validate_failed"
                    except (ValueError, TypeError):
                        pass

                    # Structured-output failures can be nondeterministic with the
                    # model. Retry once with an explicit schema-compliance reminder,
                    # while keeping strict=True and the same response schema.
                    if (
                        response_schema is not None
                        and error_code == "json_validate_failed"
                        and attempt == 0
                    ):
                        logger.warning(
                            "groq_structured_output_retry status=%s code=%s attempt=1",
                            status_code,
                            error_code,
                        )
                        continue

                    logger.warning(
                        "groq_invalid_request status=%s structured_validation_failed=%s",
                        status_code,
                        error_code == "json_validate_failed",
                    )
                    code = "invalid_request"
                elif status_code is not None and status_code >= 500:
                    code = "unavailable"
                else:
                    code = "unknown"

                raise _provider_error(code) from exc
            except requests.RequestException as exc:
                raise _provider_error("unknown") from exc
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise _provider_error("invalid_response") from exc

            if not isinstance(content, str) or not content.strip():
                raise _provider_error("invalid_response")

            return content

        raise _provider_error("invalid_response")
