import os

import requests


def _provider_error(code):
    from ai.services import AIProviderError

    return AIProviderError(code, "deepseek")


class DeepSeekProvider:
    def chat(self, messages, response_schema=None):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            raise _provider_error("authentication")

        payload = {"model": model, "messages": messages}
        if response_schema is not None:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post("https://api.deepseek.com/chat/completions", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=90)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except requests.Timeout as exc:
            raise _provider_error("timeout") from exc
        except requests.ConnectionError as exc:
            raise _provider_error("unavailable") from exc
        except requests.RequestException as exc:
            raise _provider_error("unknown") from exc
        except requests.HTTPError as exc:
            code = "rate_limit" if exc.response is not None and exc.response.status_code == 429 else "authentication" if exc.response is not None and exc.response.status_code in {401, 403} else "invalid_request" if exc.response is not None and exc.response.status_code in {400, 404, 422} else "unavailable" if exc.response is not None and exc.response.status_code >= 500 else "unknown"
            raise _provider_error(code) from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise _provider_error("invalid_response") from exc
        if not isinstance(content, str) or not content.strip():
            raise _provider_error("invalid_response")
        return content
