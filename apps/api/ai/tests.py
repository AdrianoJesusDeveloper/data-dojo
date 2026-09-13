import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import requests
from openai import (
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Conversation, Message
from .orchestrator import route_message
from .providers.gemini_provider import GeminiProvider
from .providers.openai_provider import OpenAIProvider
from .services import (
    AIProviderError,
    _provider,
    agent_runtime_status,
    chat_ai,
    chat_with_provider,
    get_provider_model,
)

from library.models import Book, BookChunk, StudioProject
from library.services.studio_agents import generate_modernization_plan


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
            "ai.services.OpenAIProvider.chat", side_effect=RuntimeError("quota indisponÃ­vel")
        ) as mocked_openai, patch(
            "ai.services.GeminiProvider.chat", return_value="Resposta do fallback Gemini"
        ) as mocked_gemini:
            answer = chat_ai("data", "Explique SQL")

            self.assertEqual(answer, "Resposta do fallback Gemini")
            mocked_openai.assert_called_once()
            mocked_gemini.assert_called_once()


@override_settings(OPENAI_API_KEY="test-placeholder-key", OPENAI_AI_MODEL="gpt-test")
class OpenAIProviderTests(TestCase):
    def _provider_with_client(self):
        sdk = patch("ai.providers.openai_provider.OpenAI").start()
        self.addCleanup(patch.stopall)
        provider = OpenAIProvider()
        return provider, sdk.return_value

    def test_classifies_known_sdk_failures_without_exposing_details(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        cases = [
            (APITimeoutError(request=request), "timeout"),
            (
                RateLimitError(
                    "sensitive rate detail",
                    response=httpx.Response(429, request=request),
                    body=None,
                ),
                "rate_limit",
            ),
            (
                AuthenticationError(
                    "sensitive auth detail",
                    response=httpx.Response(401, request=request),
                    body=None,
                ),
                "authentication",
            ),
            (
                BadRequestError(
                    "sensitive model detail",
                    response=httpx.Response(400, request=request),
                    body=None,
                ),
                "invalid_request",
            ),
            (
                InternalServerError(
                    "sensitive upstream detail",
                    response=httpx.Response(503, request=request),
                    body=None,
                ),
                "unavailable",
            ),
        ]
        for sdk_error, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                provider, client = self._provider_with_client()
                client.chat.completions.create.side_effect = sdk_error
                with self.assertRaises(AIProviderError) as raised:
                    provider.chat([{"role": "user", "content": "teste"}])
                self.assertEqual(raised.exception.code, expected_code)
                self.assertNotIn("sensitive", str(raised.exception))

    def test_rejects_empty_or_malformed_responses(self):
        malformed = [
            SimpleNamespace(choices=[]),
            SimpleNamespace(choices=[SimpleNamespace(message=None)]),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="  "))]
            ),
        ]
        for response in malformed:
            with self.subTest(response=response):
                provider, client = self._provider_with_client()
                client.chat.completions.create.return_value = response
                with self.assertRaises(AIProviderError) as raised:
                    provider.chat([{"role": "user", "content": "teste"}])
                self.assertEqual(raised.exception.code, "invalid_response")

    @override_settings(OPENAI_API_KEY="")
    def test_missing_configuration_is_normalized(self):
        with self.assertRaises(AIProviderError) as raised:
            OpenAIProvider()
        self.assertEqual(raised.exception.code, "authentication")


class GeminiProviderTests(TestCase):
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-placeholder-key"})
    @patch("ai.providers.gemini_provider.requests.post")
    def test_uses_header_authentication_without_key_in_url(self, post):
        response = Mock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Resposta"}]}}]
        }
        post.return_value = response

        self.assertEqual(
            GeminiProvider().chat([{"role": "user", "content": "teste"}]),
            "Resposta",
        )

        kwargs = post.call_args.kwargs
        self.assertNotIn("params", kwargs)
        self.assertEqual(kwargs["headers"], {"x-goog-api-key": "test-placeholder-key"})
        self.assertNotIn("test-placeholder-key", post.call_args.args[0])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-placeholder-key"})
    @patch("ai.providers.gemini_provider.requests.post")
    def test_classifies_timeout_rate_limit_and_unavailability_safely(self, post):
        post.side_effect = requests.Timeout("timeout with test-placeholder-key")
        with self.assertRaises(AIProviderError) as timeout:
            GeminiProvider().chat([{"role": "user", "content": "teste"}])
        self.assertEqual(timeout.exception.code, "timeout")

        for status_code, expected_code in ((429, "rate_limit"), (503, "unavailable")):
            with self.subTest(status_code=status_code):
                response = Mock(status_code=status_code)
                response.status_code = status_code
                response.raise_for_status.side_effect = requests.HTTPError(
                    "https://provider.invalid?key=test-placeholder-key",
                    response=response,
                )
                post.side_effect = None
                post.return_value = response
                with self.assertRaises(AIProviderError) as raised:
                    GeminiProvider().chat([{"role": "user", "content": "teste"}])
                self.assertEqual(raised.exception.code, expected_code)
                self.assertNotIn("test-placeholder-key", str(raised.exception))
                self.assertNotIn("provider.invalid", str(raised.exception))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-placeholder-key"})
    @patch("ai.providers.gemini_provider.requests.post")
    def test_rejects_invalid_response(self, post):
        response = Mock()
        response.json.return_value = {"candidates": []}
        post.return_value = response
        with self.assertRaises(AIProviderError) as raised:
            GeminiProvider().chat([{"role": "user", "content": "teste"}])
        self.assertEqual(raised.exception.code, "invalid_response")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-placeholder-key", "GEMINI_MODEL": "gemini-test"})
    @patch("ai.providers.gemini_provider.requests.post")
    def test_sends_native_structured_output_without_exposing_credentials(self, post):
        response = Mock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"decision":"GO"}' }]}}]
        }
        post.return_value = response
        schema = {
            "type": "object",
            "properties": {"decision": {"type": "string", "enum": ["GO"]}},
            "required": ["decision"],
            "additionalProperties": False,
        }

        GeminiProvider().chat([{"role": "user", "content": "teste"}], response_schema=schema)

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(payload["generationConfig"]["responseSchema"]["type"], "OBJECT")
        self.assertNotIn("additionalProperties", payload["generationConfig"]["responseSchema"])
        self.assertNotIn("test-placeholder-key", json.dumps(payload))


class ContentStudioProviderTests(TestCase):
    def _provider_response(self):
        return json.dumps(
            {
                "source_summary": "Resumo",
                "original_architecture": {},
                "proposed_architecture": {"title": "Plano"},
                "replacements": [],
                "requirements": {},
                "acceptance_criteria": [],
                "test_strategy": {},
                "risks": [],
                "business_value": "Valor",
            }
        )

    def test_settings_use_openai_when_no_server_override_exists(self):
        self.assertEqual(
            settings.CONTENT_STUDIO_PROVIDER,
            os.getenv("CONTENT_STUDIO_PROVIDER", "openai"),
        )

    @override_settings(CONTENT_STUDIO_PROVIDER="openai")
    @patch("library.services.studio_agents.validate_editorial_plan")
    @patch("library.services.studio_agents.chat_with_provider")
    def test_content_studio_selects_openai_without_client_input(self, chat, validate):
        chat.return_value = self._provider_response()
        validate.return_value = {"title": "Plano"}
        project = SimpleNamespace(
            title="Projeto", theme="Tema", objective="Objetivo", project_type="premium", original_intent=""
        )
        generate_modernization_plan(project, [])
        self.assertEqual(chat.call_args.args[0], "openai")

    @override_settings(CONTENT_STUDIO_PROVIDER="gemini")
    @patch("library.services.studio_agents.validate_editorial_plan")
    @patch("library.services.studio_agents.chat_with_provider")
    def test_explicit_server_override_can_select_gemini(self, chat, validate):
        chat.return_value = self._provider_response()
        validate.return_value = {"title": "Plano"}
        project = SimpleNamespace(
            title="Projeto", theme="Tema", objective="Objetivo", project_type="premium", original_intent=""
        )
        generate_modernization_plan(project, [])
        self.assertEqual(chat.call_args.args[0], "gemini")

    @override_settings(CONTENT_STUDIO_PROVIDER="openai")
    @patch("library.services.studio_agents.chat_with_provider", return_value="not-json")
    def test_invalid_editorial_json_remains_rejected(self, _chat):
        project = SimpleNamespace(
            title="Projeto", theme="Tema", objective="Objetivo", project_type="premium", original_intent=""
        )
        with self.assertRaises(ValueError):
            generate_modernization_plan(project, [])

    @override_settings(OPENAI_API_KEY="test-placeholder-key")
    def test_existing_aliases_remain_available(self):
        self.assertIsInstance(_provider("chatgpt"), OpenAIProvider)
        self.assertIsInstance(_provider("openai"), OpenAIProvider)
        self.assertIsInstance(_provider("gemini"), GeminiProvider)

    @override_settings(
        OPENAI_AI_MODEL="openai-model",
        CONTENT_STUDIO_MODEL="incorrect-legacy-model",
    )
    @patch.dict(
        os.environ,
        {
            "GEMINI_MODEL": "gemini-model",
            "DEEPSEEK_MODEL": "deepseek-model",
            "COPILOT_MODEL": "copilot-model",
            "GEMINI_API_KEY": "must-not-be-returned",
            "COPILOT_API_TOKEN": "must-not-be-returned",
        },
    )
    def test_provider_model_metadata_uses_each_adapter_source(self):
        self.assertEqual(get_provider_model("openai"), "openai-model")
        self.assertEqual(get_provider_model("chatgpt"), "openai-model")
        self.assertEqual(get_provider_model("gemini"), "gemini-model")
        self.assertEqual(get_provider_model("deepseek"), "deepseek-model")
        self.assertEqual(get_provider_model("copilot"), "copilot-model")
        self.assertEqual(get_provider_model("unknown"), "")
        resolved = " ".join(
            get_provider_model(name)
            for name in ("openai", "chatgpt", "gemini", "deepseek", "copilot")
        )
        self.assertNotIn("must-not-be-returned", resolved)
        self.assertNotIn("incorrect-legacy-model", resolved)

    @override_settings(OPENAI_API_KEY="test-placeholder-key")
    @patch("ai.services.GeminiProvider.chat")
    @patch("ai.services.OpenAIProvider.chat", side_effect=AIProviderError("unavailable", "openai"))
    def test_editorial_provider_call_has_no_silent_fallback(self, _openai, gemini):
        with self.assertRaises(AIProviderError):
            chat_with_provider("openai", [{"role": "user", "content": "teste"}])
        gemini.assert_not_called()


@override_settings(
    DDJ_CONTENT_STUDIO_ENABLED=True,
    DDJ_CONTENT_STUDIO_LOCAL_ONLY=True,
    CONTENT_STUDIO_PROVIDER="openai",
)
class ContentStudioProviderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="provider-editor@example.com",
            username="provider_editor",
            password="password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        book = Book.objects.create(title="Fonte", file="books/source.pdf", status="ready")
        self.project = StudioProject.objects.create(
            title="Projeto",
            theme="Tema",
            objective="Objetivo",
            created_by=self.user,
        )
        self.project.books.add(book)
        self.chunk = BookChunk.objects.create(
            book=book,
            chunk_index=0,
            page_number=1,
            content="Fonte",
        )
        self.url = reverse("library-studio-generate-plan", kwargs={"pk": self.project.pk})

    def _generation_result(self):
        return (
            {
                "source_summary": "Resumo",
                "original_architecture": {},
                "proposed_architecture": {},
                "replacements": [],
                "requirements": {},
                "acceptance_criteria": [],
                "test_strategy": {},
                "risks": [],
                "business_value": "Valor",
            },
            "raw",
        )

    @patch("library.views.buscar_chunks_relevantes")
    @patch("library.views.generate_modernization_plan")
    def test_generate_plan_accepts_empty_body(self, generate, chunks):
        chunks.return_value = [self.chunk]
        generate.return_value = self._generation_result()
        response = self.client.post(
            self.url, {}, format="json", REMOTE_ADDR="127.0.0.1"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("library.views.buscar_chunks_relevantes")
    @patch("library.views.generate_modernization_plan")
    def test_generate_plan_ignores_client_provider_and_model(self, generate, chunks):
        chunks.return_value = [self.chunk]
        generate.return_value = self._generation_result()
        response = self.client.post(
            self.url,
            {"provider": "gemini", "model": "client-controlled"},
            format="json",
            REMOTE_ADDR="127.0.0.1",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        generate.assert_called_once()
        self.assertEqual(len(generate.call_args.args), 4)

    @patch("library.views.buscar_chunks_relevantes")
    @patch(
        "library.views.generate_modernization_plan",
        side_effect=AIProviderError("unavailable", "openai"),
    )
    def test_known_provider_failure_returns_safe_503(self, _generate, chunks):
        chunks.return_value = [self.chunk]
        response = self.client.post(
            self.url, {}, format="json", REMOTE_ADDR="127.0.0.1"
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        payload = json.dumps(response.data)
        self.assertNotIn("API_KEY", payload)
        self.assertNotIn("traceback", payload.lower())
        self.assertEqual(response.data["detail"], 'Não foi possível gerar o plano editorial. Consulte o log do servidor para identificar a causa técnica.')

    @override_settings(CONTENT_STUDIO_PROVIDER="gemini")
    @patch("ai.services.OpenAIProvider.chat")
    @patch(
        "ai.services.GeminiProvider.chat",
        side_effect=AIProviderError("unavailable", "gemini"),
    )
    @patch("library.views.buscar_chunks_relevantes")
    def test_gemini_failure_does_not_fallback_to_openai(
        self, chunks, gemini, openai
    ):
        chunks.return_value = [self.chunk]
        response = self.client.post(
            self.url, {}, format="json", REMOTE_ADDR="127.0.0.1"
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data["detail"],
            'Não foi possível gerar o plano editorial. Consulte o log do servidor para identificar a causa técnica.',
        )
        gemini.assert_called_once()
        openai.assert_not_called()


@override_settings(OPENAI_API_KEY="local-test-key")
class AgentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="agente@example.com", username="agente", password="dojo-test-password"
        )

    @patch.dict("os.environ", {"AI_DEFAULT_PROVIDER": "chatgpt", "OPENAI_API_KEY": "local-test-key"})
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
        response = self.client.post(reverse("ai-chat"), {"mentor": "ai_sales", "message": "OlÃ¡"})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("ai.views.chat_ai", return_value="Comece por SELECT e pratique com uma tabela pequena.")
    def test_authenticated_agent_persists_conversation(self, mocked_chat):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("ai-chat"), {"mentor": "data", "message": "Como comeÃ§ar em SQL?"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["agent"], "data")
        self.assertEqual(Conversation.objects.filter(user=self.user, mentor="data").count(), 1)
        self.assertEqual(Message.objects.filter(conversation_id=response.data["conversation_id"]).count(), 2)
        mocked_chat.assert_called_once()

    @patch("ai.views.chat_ai", return_value="Resposta comercial")
    def test_anonymous_conversation_requires_its_private_token(self, mocked_chat):
        first = self.client.post(
            reverse("ai-chat"),
            {"mentor": "ai_sales", "message": "Quero conhecer os cursos."},
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertTrue(first.data["conversation_token"])

        attacker = APIClient()
        denied = attacker.post(
            reverse("ai-chat"),
            {
                "mentor": "ai_sales",
                "message": "Continue a conversa.",
                "conversation_id": first.data["conversation_id"],
                "conversation_token": "token-incorreto",
            },
        )
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)

        allowed = self.client.post(
            reverse("ai-chat"),
            {
                "mentor": "ai_sales",
                "message": "Continue a conversa.",
                "conversation_id": first.data["conversation_id"],
                "conversation_token": first.data["conversation_token"],
            },
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertNotIn("conversation_token", allowed.data)
