import os

import requests


class GeminiProvider:
    """Provider Gemini usando a API REST oficial configurada no backend."""

    def chat(self, messages):
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY não configurada.")

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

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
