import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from ai.providers.groq_provider import GroqProvider
from ai.services import AIProviderError
from library.editorial_contracts import editorial_plan_schema, get_editorial_contract, validate_editorial_plan
from library.services.studio_agents import generate_content_item, generate_modernization_plan
from library.tests.test_editorial_contracts import valid_plan


class EditorialAuditTests(SimpleTestCase):
    def test_schema_and_declarative_fields_match_at_every_level(self):
        for kind in ("premium", "youtube"):
            contract = get_editorial_contract(kind)
            schema = editorial_plan_schema(kind)
            self.assertEqual(set(schema["required"]), set(contract["plan_required_fields"]))
            item = schema["properties"][contract["content_collection"]]["items"]
            self.assertEqual(set(item["required"]), set(contract["content_required_fields"]))
            if kind == "premium":
                self.assertEqual(set(item["properties"]["lessons"]["items"]["required"]), set(contract["lesson_required_fields"]))

    def test_every_required_premium_field_is_enforced(self):
        contract = get_editorial_contract("premium")
        for level, required in (("plan", "plan_required_fields"), ("module", "content_required_fields"), ("lesson", "lesson_required_fields")):
            for field in contract[required]:
                plan = valid_plan("premium")
                target = plan if level == "plan" else plan["modules"][0] if level == "module" else plan["modules"][0]["lessons"][0]
                del target[field]
                with self.subTest(level=level, field=field), self.assertRaises(ValueError):
                    validate_editorial_plan("premium", plan)

    @patch("library.services.studio_agents.chat_with_provider")
    def test_recording_rejects_empty_editorial_fields_outside_recording_contract(self, chat):
        from library.tests.test_studio_recording import script
        project = SimpleNamespace(pk=1, title="Plano", theme="Tema", objective="Objetivo", project_type="premium")
        plan = SimpleNamespace(proposed_architecture=valid_plan("premium"), source_summary="Sem fontes")
        for value in (None, "", [], False, "   "):
            content = script("premium")
            content["mini_project"] = value
            chat.return_value = json.dumps({"content": content})
            with self.subTest(value=value), self.assertRaises(ValueError):
                generate_content_item(project, plan, "lesson", 0, {})

    def test_declarative_premium_lesson_includes_title(self):
        self.assertIn("title", get_editorial_contract("premium")["lesson_required_fields"])

    def test_malformed_collections_raise_validation_errors(self):
        for value in (None, "invalid", [None], ["invalid"]):
            for level in ("modules", "lessons"):
                plan = valid_plan("premium")
                if level == "modules":
                    plan["modules"] = value
                else:
                    plan["modules"][0]["lessons"] = value
                with self.subTest(level=level, value=value), self.assertRaises(ValueError):
                    validate_editorial_plan("premium", plan)

    @patch("library.services.studio_agents.chat_with_provider")
    def test_generation_rejects_missing_editorial_content_instead_of_inventing_it(self, chat):
        project = SimpleNamespace(title="Plano", theme="Tema", objective="Objetivo", original_intent="Formar", project_type="premium")
        for level, fields in (
            ("plan", ["final_project", "completion_requirements", "certification_requirements"]),
            ("module", ["kata", "practical_project", "assessment"]),
            ("lesson", ["authorship_challenge"]),
        ):
            for field in fields:
                for value in (None, "", {}, [], False):
                    plan = valid_plan("premium")
                    target = plan if level == "plan" else plan["modules"][0] if level == "module" else plan["modules"][0]["lessons"][0]
                    target[field] = value
                    response = dict(source_summary="Resumo", original_architecture={}, proposed_architecture=plan,
                                    replacements=[], requirements={}, acceptance_criteria=[], test_strategy={}, risks=[], business_value="Valor")
                    chat.return_value = json.dumps(response)
                    with self.subTest(level=level, field=field, value=value), self.assertRaises(ValueError):
                        generate_modernization_plan(project, [])


@patch.dict("os.environ", {"GROQ_API_KEY": "test-secret"})
class GroqAuditTests(SimpleTestCase):
    schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"], "additionalProperties": False}

    def response(self, status, code="json_validate_failed"):
        response = Mock(status_code=status, headers={})
        response.json.return_value = {"error": {"code": code, "message": "test-secret", "failed_generation": "private-model-output"}}
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        return response

    @patch("ai.providers.groq_provider.requests.post")
    def test_strict_schema_retries_at_most_once_without_logging_response(self, post):
        post.return_value = self.response(400)
        with self.assertLogs("ai.providers.groq_provider", level="WARNING") as logs:
            with self.assertRaises(AIProviderError):
                GroqProvider().chat([], response_schema=self.schema)
        self.assertEqual(post.call_count, 2)
        for call in post.call_args_list:
            contract = call.kwargs["json"]["response_format"]["json_schema"]
            self.assertTrue(contract["strict"])
            self.assertEqual(contract["schema"], self.schema)
        self.assertNotIn("test-secret", " ".join(logs.output))
        self.assertNotIn("private-model-output", " ".join(logs.output))

    @patch("ai.providers.groq_provider.requests.post")
    def test_authentication_and_rate_limit_never_retry(self, post):
        for status, code in ((401, "authentication"), (403, "authentication"), (429, "rate_limit")):
            post.reset_mock()
            post.return_value = self.response(status)
            with self.subTest(status=status), self.assertRaises(AIProviderError) as raised:
                GroqProvider().chat([], response_schema=self.schema)
            self.assertEqual(raised.exception.code, code)
            self.assertEqual(post.call_count, 1)
