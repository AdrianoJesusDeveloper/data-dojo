from openai import OpenAI

from django.conf import settings


class OpenAIProvider:

    def __init__(self):

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def chat(self, message: str):

        response = self.client.chat.completions.create(

            model="gpt-4.1-mini",

            messages=[

                {
                    "role": "system",
                    "content":
                        """
                        Você é o Sensei ChatGPT
                        do Data Driven Dojô.

                        Ensine programação,
                        Python,
                        SQL,
                        IA,
                        Cloud,
                        Ciência de Dados.

                        Seja didático,
                        objetivo
                        e incentive o aluno.
                        """
                },

                {
                    "role": "user",
                    "content": message
                }

            ]

        )

        return response.choices[0].message.content