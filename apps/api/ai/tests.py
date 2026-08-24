from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Conversation, Message
from .orchestrator import route_message
from .services import agent_runtime_status
from .services import chat_ai


class AgentRuntimeTests(TestCase):
    def test_router_selects_specialists(self):
        self.assertEqual(route_message("Quero aprender SQL e Python"), "data")
        self.assertEqual(route_message("Como publicar meu projeto na AWS?"), "cloud")
        self.assertEqual(route_message("Ajude com meu currículo"), "career")

    @patch.dict(
        "os.environ",
        {"AI_DEFAULT_PROVIDER": "chatgpt", "OPENAI_API_KEY": "local-test-key"},
    )
    def test_openai_agent_reports_available_without_exposing_key(self):
        runtime = agent_runtime_status({"provider_env": "DATA_AI_PROVIDER", "default_provider": "chatgpt"})
        self.assertEqual(runtime, {"provider": "chatgpt", "available": True})
        self.assertNotIn("key", runtime)

    @patch.dict(
        "os.environ",
        {"ENVIRONMENT": "production", "AI_ENABLED": "false", "OPENAI_API_KEY": "local-test-key"},
    )
    def test_agents_are_disabled_in_production_even_with_a_key(self):
        runtime = agent_runtime_status({"provider_env": "DATA_AI_PROVIDER", "default_provider": "chatgpt"})
        self.assertFalse(runtime["available"])
        self.assertIn(runtime["provider"], {"chatgpt", "gemini"})

    @patch.dict(
        "os.environ",
        {
            "AI_DEFAULT_PROVIDER": "chatgpt",
            "OPENAI_API_KEY": "local-test-key",
            "GEMINI_API_KEY": "gemini-test-key",
        },
    )
    @override_settings(OPENAI_API_KEY="local-test-key")
    def test_chat_falls_back_to_gemini(self):
        with patch(
            "ai.services.OpenAIProvider.chat", side_effect=RuntimeError("quota indisponível")
        ) as mocked_openai, patch(
            "ai.services.GeminiProvider.chat", return_value="Resposta do fallback Gemini"
        ) as mocked_gemini:
            answer = chat_ai("data", "Explique SQL")

            self.assertEqual(answer, "Resposta do fallback Gemini")
            mocked_openai.assert_called_once()
            mocked_gemini.assert_called_once()


@override_settings(OPENAI_API_KEY="local-test-key")
class AgentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="agente@example.com", username="agente", password="dojo-test-password"
        )

    @patch.dict("os.environ", {"OPENAI_API_KEY": "local-test-key"})
    def test_anonymous_user_sees_only_public_agent(self):
        response = self.client.get(reverse("ai-agents"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([agent["key"] for agent in response.data["agents"]], ["ai_sales"])
        self.assertTrue(response.data["agents"][0]["available"])

    def test_private_agent_requires_authentication(self):
        response = self.client.post(reverse("ai-chat"), {"mentor": "data", "message": "Explique SQL."})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch.dict("os.environ", {"AI_ENABLED": "false"})
    def test_chat_is_unavailable_when_ai_is_disabled(self):
        response = self.client.post(reverse("ai-chat"), {"mentor": "ai_sales", "message": "Olá"})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("ai.views.chat_ai", return_value="Comece por SELECT e pratique com uma tabela pequena.")
    def test_authenticated_agent_persists_conversation(self, mocked_chat):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("ai-chat"), {"mentor": "data", "message": "Como começar em SQL?"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["agent"], "data")
        self.assertEqual(Conversation.objects.filter(user=self.user, mentor="data").count(), 1)
        self.assertEqual(Message.objects.filter(conversation_id=response.data["conversation_id"]).count(), 2)
        mocked_chat.assert_called_once()
