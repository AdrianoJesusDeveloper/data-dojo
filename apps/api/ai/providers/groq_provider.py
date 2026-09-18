import json
import logging
import os

import requests


logger = logging.getLogger(__name__)


def _payload_size_bytes(payload):
    """Return the UTF-8 size of the JSON body without logging its content."""
    return len(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _safe_error_metadata(response):
    """Extract only small diagnostic metadata from Groq's error envelope."""
    error_type = None
    error_code = None
    error_message = None

    try:
        body = response.json()
    except (ValueError, TypeError):
        body = None

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            raw_type = error.get("type")
            raw_code = error.get("code")
            raw_message = error.get("message")

            error_type = str(raw_type)[:120] if raw_type is not None else None
            error_code = str(raw_code)[:120] if raw_code is not None else None
            # Keep this short and only in local server logs. Do not return it
            # directly to the frontend because provider messages are not part
            # of the public API contract.
            error_message = str(raw_message)[:500] if raw_message is not None else None

    return {
        "type": error_type,
        "code": error_code,
        "message": error_message,
    }


def _looks_like_rate_limit_413(metadata):
    """Some upstreams describe token/rate ceilings using HTTP 413.

    Groq documents 413 primarily as an oversized request body, so we preserve
    payload_too_large unless the provider's own message explicitly identifies
    a token/rate limit.
    """
    message = (metadata.get("message") or "").lower()
    return any(
        marker in message
        for marker in (
            "tokens per minute",
            "token per minute",
            "tpm",
            "rate limit",
            "rate_limit",
        )
    )


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
        plan_schema = bool(
            isinstance(response_schema, dict)
            and isinstance(response_schema.get("properties"), dict)
            and "proposed_architecture" in response_schema["properties"]
        )
        # Preserve the historical one-retry contract for strict structured
        # outputs, but never retry modernization-plan generation. The plan uses
        # prompt JSON + backend validation specifically to avoid TPM double spend.
        max_attempts = 2 if response_schema is not None and not plan_schema else 1

        for attempt in range(max_attempts):
            request_messages = list(base_messages)
            if attempt == 1:
                request_messages.append(
                    {
                        "role": "system",
                        "content": (
                            "A geração estruturada anterior não correspondeu ao JSON Schema. "
                            "Tente novamente obedecendo estritamente ao schema fornecido. "
                            "Inclua todas as propriedades obrigatórias, respeite os tipos "
                            "e não acrescente propriedades extras."
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
                if not plan_schema:
                    payload["response_format"] = {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "ddj_structured_response",
                            "strict": True,
                            "schema": response_schema,
                        },
                    }
                # Para o plano de modernização, NÃO usamos response_format no Groq.
                # O modelo recebe instrução explícita para devolver JSON e o backend
                # faz parsing, normalização segura e validação canônica completa.

            request_bytes = _payload_size_bytes(payload)
            message_chars = sum(
                len(message.get("content", ""))
                for message in request_messages
                if isinstance(message, dict) and isinstance(message.get("content"), str)
            )
            schema_chars = (
                len(json.dumps(response_schema, ensure_ascii=False, separators=(",", ":")))
                if response_schema is not None
                else 0
            )
            logger.info(
                "groq_request model=%s attempt=%s request_bytes=%s message_chars=%s "
                "schema_chars=%s max_completion_tokens=%s structured=%s structured_mode=%s",
                model,
                attempt + 1,
                request_bytes,
                message_chars,
                schema_chars,
                payload["max_completion_tokens"],
                response_schema is not None,
                (
                    "prompt_json_backend_validated"
                    if plan_schema
                    else ("json_schema_strict" if response_schema is not None else "none")
                ),
            )

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
                metadata = _safe_error_metadata(response) if response is not None else {
                    "type": None,
                    "code": None,
                    "message": None,
                }

                if response is not None:
                    logger.warning(
                        "groq_http_error status=%s model=%s request_bytes=%s "
                        "provider_type=%s provider_code=%s "
                        "retry_after=%s limit_tokens=%s remaining_tokens=%s reset_tokens=%s",
                        status_code,
                        model,
                        request_bytes,
                        metadata["type"],
                        metadata["code"],
                        response.headers.get("retry-after"),
                        response.headers.get("x-ratelimit-limit-tokens"),
                        response.headers.get("x-ratelimit-remaining-tokens"),
                        response.headers.get("x-ratelimit-reset-tokens"),
                    )

                if status_code == 413:
                    code = "rate_limit" if _looks_like_rate_limit_413(metadata) else "payload_too_large"
                elif status_code == 429:
                    code = "rate_limit"
                elif status_code in {401, 403}:
                    code = "authentication"
                elif status_code in {400, 404, 422}:
                    error_code = metadata["code"]

                    if (
                        response_schema is not None
                        and not plan_schema
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
                    code = "invalid_response" if error_code == "json_validate_failed" else "invalid_request"
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
