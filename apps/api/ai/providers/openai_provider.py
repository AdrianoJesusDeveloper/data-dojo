from openai import OpenAI

from django.conf import settings


class OpenAIProvider:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def chat(self, messages):
        response = self.client.chat.completions.create(
            model=getattr(settings, "OPENAI_AI_MODEL", "gpt-4.1-mini"),
            messages=messages,
        )
        return response.choices[0].message.content
