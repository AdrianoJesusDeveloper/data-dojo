import io
import zipfile
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from pypdf import PdfReader
from rest_framework import status
from rest_framework.test import APITestCase

from professional.models import Opportunity, OpportunityProposal


PROPOSAL_DATA = {
    "greeting": "Olá, equipe do cliente.",
    "understanding": "Entendemos a necessidade de organizar o processo comercial.",
    "approach": "Trabalharemos com validações incrementais.",
    "deliverables": ["Painel comercial", "Documentação editável"],
    "deadline": "Quatro semanas após a aprovação.",
    "suggested_price": "12500.00",
    "currency": "BRL",
    "essential_questions": ["Quem aprovará cada etapa?"],
    "differentiators": ["Comunicação objetiva", "Critérios de aceite"],
    "closing": "Ficamos à disposição para o próximo passo.",
    "ai_provider": "provider-interno-secreto",
    "ai_model": "modelo-interno-secreto",
}


class OpportunityProposalExportTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="proposal-owner", email="proposal-owner@example.com", password="pass", is_staff=True)
        self.other = users.objects.create_user(username="proposal-other", email="proposal-other@example.com", password="pass", is_staff=True)
        self.opportunity = Opportunity.objects.create(
            created_by=self.owner, title="Transformação Comercial", client_name="Cliente Exemplo",
            description="Escopo persistido", source="DIRECT_CLIENT", currency="BRL",
        )
        self.client.force_authenticate(self.owner)

    def create_proposal(self, version="CONSULTATIVE", status_value="DRAFT"):
        return OpportunityProposal.objects.create(
            opportunity=self.opportunity, created_by=self.owner, version=version,
            status=status_value, **PROPOSAL_DATA,
        )

    def export(self, version, extension):
        return self.client.get(
            f"/api/professional/opportunities/{self.opportunity.id}/proposal/export/{extension}/",
            {"version": version},
        )

    @patch("professional.services.chat_with_provider")
    def test_exports_pdf_and_docx_from_persisted_proposal_without_ai_or_mutation(self, provider):
        proposal = self.create_proposal(status_value="APPROVED")
        proposal.refresh_from_db()
        before = deepcopy({field.name: getattr(proposal, field.name) for field in proposal._meta.concrete_fields})

        pdf = self.export("CONSULTATIVE", "pdf")
        self.assertEqual(pdf.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("proposta-transformacao-comercial-consultative.pdf", pdf["Content-Disposition"])
        self.assertTrue(pdf.content.startswith(b"%PDF-"))
        pdf_text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages)
        self.assertIn("PROPOSTA COMERCIAL", pdf_text)
        self.assertIn("Cliente Exemplo", pdf_text)
        self.assertIn("Painel comercial", pdf_text)

        docx = self.export("CONSULTATIVE", "docx")
        self.assertEqual(docx.status_code, status.HTTP_200_OK)
        self.assertEqual(docx["Content-Type"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(docx.content)))
        with zipfile.ZipFile(io.BytesIO(docx.content)) as archive:
            docx_xml = " ".join(archive.read(name).decode("utf-8", "ignore") for name in archive.namelist() if name.endswith(".xml"))
        self.assertIn("PROPOSTA COMERCIAL", docx_xml)
        self.assertIn("Documentação editável", docx_xml)

        for exported in (pdf_text, docx_xml):
            self.assertNotIn("provider-interno-secreto", exported)
            self.assertNotIn("modelo-interno-secreto", exported)
            self.assertNotIn("raw_response", exported)
        proposal.refresh_from_db()
        after = {field.name: getattr(proposal, field.name) for field in proposal._meta.concrete_fields}
        self.assertEqual(before, after)
        provider.assert_not_called()

    def test_all_proposal_versions_are_exportable(self):
        for version in OpportunityProposal.Version.values:
            with self.subTest(version=version):
                self.create_proposal(version=version)
                response = self.export(version, "pdf")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(response.content)).pages)
                self.assertIn({"SHORT": "Curta", "CONSULTATIVE": "Consultiva", "TECHNICAL": "Técnica"}[version], text)

    def test_missing_proposal_returns_404_and_invalid_version_returns_400(self):
        self.assertEqual(self.export("CONSULTATIVE", "pdf").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.export("UNKNOWN", "pdf").status_code, status.HTTP_400_BAD_REQUEST)

    @patch("professional.services.chat_with_provider")
    def test_other_owner_is_isolated_and_export_never_calls_ai(self, provider):
        self.create_proposal()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.export("CONSULTATIVE", "docx").status_code, status.HTTP_404_NOT_FOUND)
        provider.assert_not_called()
