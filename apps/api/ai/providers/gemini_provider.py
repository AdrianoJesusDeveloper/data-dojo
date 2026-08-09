class GeminiProvider:

    def chat(self, message: str):
        return (
            "Gemini ainda não foi configurado.\n\n"
            f"Mensagem recebida: {message}"
        )