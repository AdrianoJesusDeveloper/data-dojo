import os

import requests


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
            raise RuntimeError(
                "COPILOT_API_URL não configurada. "
                "Configure um endpoint compatível com Chat Completions."
            )

    def chat(self, messages):
        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": messages,
            },
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
