import os

import requests


def _provider_error(code):
    from ai.services import AIProviderError

    return AIProviderError(code, "copilot")


class GitHubCopilotProvider:
    """
    Adapter para um backend GitHub Copilot/Copilot SDK exposto como
    endpoint OpenAI-compatible de Chat Completions.

    O endpoint e as credenciais ficam somente no backend:
    COPILOT_API_URL, COPILOT_API_TOKEN e COPILOT_MODEL.
    """

    def __init__(self):
        self.base_url = os.getenv("COPILOT_API_URL", "").rstrip("/")
        self.token = os.getenv("COPILOT_API_TOKEN", "")
        self.model = os.getenv("COPILOT_MODEL", "gpt-5.4")

        if not self.base_url:
            raise _provider_error("authentication")

    def chat(self, messages, response_schema=None):
        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        payload = {
            "model": self.model,
            "messages": messages,
        }
        if response_schema is not None:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=90)
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
