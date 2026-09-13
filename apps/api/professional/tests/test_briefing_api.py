import json
import io
import zipfile
from unittest.mock import patch

from pypdf import PdfReader

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ai.services import AIProviderError
from professional.models import Opportunity, OpportunityBriefing


VALID_BRIEFING = {
    "problem": "Processo comercial manual.", "objective": "Automatizar o atendimento.",
    "target_audience": "Equipe comercial", "deliverables": ["Painel web"],
    "functional_requirements": ["Cadastrar leads"], "non_functional_requirements": ["Acesso seguro"],
    "integrations": ["CRM"], "data_requirements": ["Base de clientes"],
    "infrastructure_requirements": ["Hospedagem web"], "constraints": ["Prazo informado"],
    "dependencies": ["Acesso ao CRM"], "assumptions": ["API do CRM disponível"],
    "scope_risks": ["Mudança de escopo"], "ambiguities": ["Volume não informado"],
    "client_questions": ["Qual o volume diário?"], "acceptance_criteria": ["Lead sincronizado"],
}


class OpportunityBriefingApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="brief-owner", email="brief-owner@example.com", password="test-pass", is_staff=True)
        self.other = user_model.objects.create_user(username="brief-other", email="brief-other@example.com", password="test-pass", is_staff=True)
        self.opportunity = Opportunity.objects.create(created_by=self.owner, title="Automação comercial", description="Cliente precisa automatizar cadastro de leads no CRM.", source="DIRECT_CLIENT", currency="BRL")

    @property
    def generate_url(self):
        return f"/api/professional/opportunities/{self.opportunity.id}/generate-briefing/"

    @property
    def briefing_url(self):
        return f"/api/professional/opportunities/{self.opportunity.id}/briefing/"

    @patch.dict("os.environ", {"PROFESSIONAL_BRIEFING_PROVIDER": "test-provider"})
    @patch("professional.services.get_provider_model", return_value="test-model")
    @patch("professional.services.chat_with_provider", return_value=json.dumps(VALID_BRIEFING))
    def test_owner_generates_valid_persisted_briefing_with_metadata(self, chat, _model):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.generate_url, {"additional_context": "Priorizar segurança."}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        briefing = OpportunityBriefing.objects.get(opportunity=self.opportunity)
        self.assertEqual(briefing.created_by, self.owner)
        self.assertEqual(briefing.ai_provider, "test-provider")
        self.assertEqual(briefing.ai_model, "test-model")
        self.assertEqual(response.data["deliverables"], ["Painel web"])
        messages = chat.call_args.args[1]
        prompt = messages[1]["content"]
        self.assertIn(self.opportunity.description, prompt)
        self.assertIn("Priorizar segurança", prompt)

    def test_anonymous_is_rejected(self):
        self.assertEqual(self.client.post(self.generate_url, {}, format="json").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.briefing_url).status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("professional.services.chat_with_provider")
    def test_other_user_cannot_generate_read_or_edit(self, chat):
        OpportunityBriefing.objects.create(opportunity=self.opportunity, created_by=self.owner, raw_source_text=self.opportunity.description, ai_provider="test", **VALID_BRIEFING)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(self.generate_url, {}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(self.briefing_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(self.briefing_url, {"problem": "Ataque"}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        chat.assert_not_called()

    @patch("professional.services.chat_with_provider")
    def test_empty_description_is_rejected_before_provider(self, chat):
        self.opportunity.description = "   "
        self.opportunity.save(update_fields=["description"])
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.generate_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        chat.assert_not_called()

    @patch("professional.services.chat_with_provider", return_value="not-json")
    def test_invalid_json_is_sanitized_and_not_persisted(self, _chat):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.generate_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["code"], "invalid_response")
        self.assertFalse(OpportunityBriefing.objects.exists())
        self.assertNotIn("not-json", json.dumps(response.data))

    @patch("professional.services.chat_with_provider", side_effect=AIProviderError("rate_limit", "secret-provider"))
    def test_provider_error_becomes_safe_response(self, _chat):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.generate_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["code"], "rate_limit")
        self.assertNotIn("secret-provider", json.dumps(response.data))
        self.assertFalse(OpportunityBriefing.objects.exists())

    def test_get_and_manual_edit_work_for_owner(self):
        briefing = OpportunityBriefing.objects.create(opportunity=self.opportunity, created_by=self.owner, raw_source_text=self.opportunity.description, ai_provider="test", **VALID_BRIEFING)
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.briefing_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["problem"], VALID_BRIEFING["problem"])
        response = self.client.patch(self.briefing_url, {"problem": "Problema revisado", "deliverables": ["Painel", "API"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        briefing.refresh_from_db()
        self.assertEqual(briefing.problem, "Problema revisado")
        self.assertEqual(briefing.deliverables, ["Painel", "API"])

    def test_get_without_briefing_returns_404(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(self.briefing_url).status_code, status.HTTP_404_NOT_FOUND)

    def create_briefing(self):
        return OpportunityBriefing.objects.create(opportunity=self.opportunity, created_by=self.owner, raw_source_text="SEGREDO INTERNO", ai_provider="test", **VALID_BRIEFING)

    @patch("professional.services.chat_with_provider")
    def test_owner_exports_all_formats_without_calling_ai(self, provider):
        self.create_briefing()
        self.client.force_authenticate(self.owner)
        expected = {
            "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", "md": "text/markdown; charset=utf-8",
            "json": "application/json; charset=utf-8",
        }
        for extension, mime in expected.items():
            with self.subTest(extension=extension):
                response = self.client.get(f"{self.briefing_url}export/{extension}/")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response["Content-Type"], mime)
                self.assertIn(f"briefing-automacao-comercial.{extension}", response["Content-Disposition"])
                self.assertGreater(len(response.content), 100)
                if extension in {"docx", "pptx"}:
                    self.assertTrue(zipfile.is_zipfile(io.BytesIO(response.content)))
                    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                        xml = " ".join(
                            archive.read(name).decode("utf-8", "ignore")
                            for name in archive.namelist() if name.endswith(".xml")
                        )
                    self.assertIn("3DS Marketing Digital &amp; Tecnologia", xml)
                    self.assertNotIn("test-provider", xml)
                    self.assertNotIn("test-model", xml)
                elif extension == "pdf":
                    self.assertTrue(response.content.startswith(b"%PDF-"))
                    text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(response.content)).pages)
                    self.assertIn("3DS Marketing Digital & Tecnologia", text)
                    self.assertIn("BRIEFING PROFISSIONAL", text)
                    self.assertNotIn("test-provider", text)
                    self.assertNotIn("test-model", text)
                else:
                    self.assertIn("Autom", response.content.decode("utf-8"))
                self.assertNotIn(b"SEGREDO INTERNO", response.content)
        provider.assert_not_called()

    def test_exports_omit_unknown_client_and_empty_sections(self):
        briefing = self.create_briefing()
        briefing.client_questions = []
        briefing.save(update_fields=["client_questions"])
        self.client.force_authenticate(self.owner)
        for extension in ("pdf", "docx", "pptx"):
            with self.subTest(extension=extension):
                response = self.client.get(f"{self.briefing_url}export/{extension}/")
                self.assertNotIn(b"Cliente Teste", response.content)
                if extension == "pdf":
                    text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(response.content)).pages)
                    self.assertNotIn("Perguntas para alinhamento", text)
                else:
                    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                        xml = " ".join(archive.read(name).decode("utf-8", "ignore") for name in archive.namelist() if name.endswith(".xml"))
                    self.assertNotIn("Perguntas para alinhamento", xml)

    @patch("professional.services.chat_with_provider")
    def test_export_is_owner_isolated_and_never_calls_ai(self, provider):
        self.create_briefing()
        self.client.force_authenticate(self.other)
        response = self.client.get(f"{self.briefing_url}export/pdf/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        provider.assert_not_called()

    def test_export_requires_briefing_and_rejects_invalid_format(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(f"{self.briefing_url}export/pdf/").status_code, status.HTTP_404_NOT_FOUND)
        self.create_briefing()
        self.assertEqual(self.client.get(f"{self.briefing_url}export/exe/").status_code, status.HTTP_404_NOT_FOUND)
