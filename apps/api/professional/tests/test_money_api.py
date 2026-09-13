import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ai.services import AIProviderError
from professional.models import Opportunity, OpportunityAnalysis, OpportunityExecutionPlan, OpportunityProposal
from professional.services import (
    ANALYSIS_RESPONSE_SCHEMA, PROPOSAL_RESPONSE_SCHEMA, generate_opportunity_analysis,
    generate_opportunity_proposal, validate_analysis_payload,
)


VALID_ANALYSIS = {
    "decision": "CAUTION", "score": 68, "problem_summary": "Automatizar relatórios",
    "client_need": "Reduzir trabalho manual", "likely_deliverables": ["Pipeline", "Dashboard"],
    "technologies": ["Python"], "required_competencies": ["ETL"], "complexity": "Média",
    "technical_risks": ["API não documentada"], "commercial_risks": ["Escopo aberto"],
    "ambiguities": ["Volume de dados"], "missing_information": ["Credenciais de teste"],
    "client_questions": ["Qual o volume?"], "external_dependencies": ["API do cliente"],
    "estimated_deadline": "2 a 4 semanas",
    "estimated_effort": {"minimum": "40h", "probable": "60h", "with_margin": "80h", "suggested_deadline": "4 semanas", "schedule_risks": ["Acesso tardio"]},
    "ai_execution_fit": "IA auxilia documentação; integração exige validação humana.",
    "competency_gap": {"can_execute": ["Python"], "with_ai_support": ["Documentação"], "study_first": ["API específica"], "do_not_assume": ["Infraestrutura sem acesso"]},
    "score_breakdown": {"scope_clarity": 8, "technical_domain": 12, "risk": 8, "deadline": 10, "dependencies": 8, "validation": 12, "ai_fit": 10},
    "pricing": {"insufficient_data": False, "suggested_range": "R$ 4.000–6.000", "minimum_recommended": "R$ 4.000", "target": "R$ 5.500", "justification": "Esforço e risco", "change_factors": ["Volume"]},
    "limitations": ["Sem matriz persistente de competências; revisão humana obrigatória."],
}
VALID_PROPOSAL = {
    "greeting": "Olá!", "understanding": "Você precisa automatizar relatórios recorrentes.",
    "approach": "Validar fontes, construir pipeline e homologar o dashboard.",
    "deliverables": ["Pipeline", "Dashboard"], "deadline": "4 semanas",
    "suggested_price": 5500, "currency": "BRL", "essential_questions": ["Qual o volume?"],
    "differentiators": ["Validação incremental"], "closing": "Podemos alinhar os acessos antes de iniciar?",
}
VALID_PLAN = {
    "project": "Automação de relatórios",
    "phases": [{"name": "Descoberta", "acceptance_criteria": ["Fontes homologadas"], "tasks": [{
        "objective": "Validar dados", "description": "Inspecionar amostras", "dependencies": ["Acesso"],
        "tools": ["Python"], "expected_result": "Mapa de dados", "validation": "Revisão com cliente",
        "ai_help": "Rascunhar documentação", "human_validation": "Confirmar regras de negócio",
    }]}],
    "risks": ["Acesso tardio"], "validation": ["Homologação por fase"], "delivery": ["Código", "Documentação"],
}


class MoneyWorkflowApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username="money-owner", email="money-owner@example.com", password="pass", is_staff=True)
        self.other = users.objects.create_user(username="money-other", email="money-other@example.com", password="pass", is_staff=True)
        self.student = users.objects.create_user(username="money-student", email="money-student@example.com", password="pass")
        self.opportunity = Opportunity.objects.create(
            created_by=self.owner, title="Automação comercial", description="Integrar API e gerar dashboard semanal.",
            source=Opportunity.Source.FREELAS_99, budget_min=4000, budget_max=6000,
        )
        self.base = f"/api/professional/opportunities/{self.opportunity.id}/"

    @patch("professional.views.generate_opportunity_analysis", return_value=(VALID_ANALYSIS, "gemini", "safe-model"))
    def test_analysis_is_persistent_validated_and_audited(self, _generate):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.base + "analyze/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data["decision"], {"GO", "CAUTION", "NO_GO"})
        self.assertGreaterEqual(response.data["score"], 0)
        self.assertLessEqual(response.data["score"], 100)
        analysis = OpportunityAnalysis.objects.get(opportunity=self.opportunity)
        self.assertEqual(analysis.ai_provider, "gemini")
        self.assertEqual(analysis.ai_model, "safe-model")
        self.assertEqual(self.client.get(self.base + "analysis/").data["id"], analysis.id)

    def test_invalid_decision_and_score_are_rejected_by_schema(self):
        for changes in ({"decision": "MAYBE"}, {"score": 101}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    validate_analysis_payload(json.dumps({**VALID_ANALYSIS, **changes}))

    @patch("professional.services.get_provider_model", return_value="gemini-test")
    @patch("professional.services.configured_briefing_provider", return_value="gemini")
    @patch("professional.services.chat_with_provider", return_value=json.dumps(VALID_ANALYSIS))
    def test_real_analysis_path_requests_structured_output_from_central_gateway(self, chat, _provider, _model):
        opportunity = SimpleNamespace(
            title="Sintética", description="Página estática", source="99FREELAS",
            source_url="", budget_min=None, budget_max=None, currency="BRL",
            deadline=None, notes="",
        )
        payload, provider, model = generate_opportunity_analysis(opportunity)
        self.assertEqual((provider, model, payload["decision"]), ("gemini", "gemini-test", "CAUTION"))
        self.assertEqual(chat.call_args.kwargs["response_schema"], ANALYSIS_RESPONSE_SCHEMA)

    @patch("professional.services.get_provider_model", return_value="gemini-test")
    @patch("professional.services.configured_briefing_provider", return_value="gemini")
    @patch("professional.services.chat_with_provider", return_value=json.dumps(VALID_PROPOSAL))
    def test_all_proposal_versions_request_their_strict_structured_output(self, chat, _provider, _model):
        opportunity = SimpleNamespace(
            title="Sintética", description="Página estática", source="99FREELAS",
            source_url="", budget_min=None, budget_max=None, currency="BRL",
            deadline=None, notes="",
        )
        analysis = SimpleNamespace(
            decision="CAUTION", problem_summary="Criar página", client_need="Presença digital",
            likely_deliverables=["Página"], client_questions=["Qual o conteúdo?"], pricing={},
        )
        for version in ("SHORT", "CONSULTATIVE", "TECHNICAL"):
            with self.subTest(version=version):
                payload, provider, model = generate_opportunity_proposal(opportunity, analysis, version)
                self.assertEqual((provider, model, payload["currency"]), ("gemini", "gemini-test", "BRL"))
                self.assertEqual(chat.call_args.kwargs["response_schema"], PROPOSAL_RESPONSE_SCHEMA)
                self.assertIn(version, chat.call_args.args[1][0]["content"])

    def test_student_is_forbidden_and_other_staff_is_isolated(self):
        for user, expected in ((self.student, 403), (self.other, 404)):
            with self.subTest(user=user.username):
                self.client.force_authenticate(user)
                self.assertEqual(self.client.post(self.base + "analyze/", {}, format="json").status_code, expected)

    @patch("professional.views.generate_opportunity_analysis", side_effect=AIProviderError("authentication", "secret-key-value"))
    def test_provider_error_is_safe_and_exposes_no_key(self, _generate):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.base + "analyze/", {}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret-key-value", json.dumps(response.data))
        self.assertFalse(OpportunityAnalysis.objects.exists())

    @patch("professional.views.generate_opportunity_proposal", return_value=(VALID_PROPOSAL, "gemini", "safe-model"))
    def test_proposal_starts_draft_can_be_edited_and_requires_explicit_approval(self, _generate):
        OpportunityAnalysis.objects.create(opportunity=self.opportunity, created_by=self.owner, ai_provider="test", **VALID_ANALYSIS)
        self.client.force_authenticate(self.owner)
        generated = self.client.post(self.base + "generate-proposal/", {"version": "CONSULTATIVE", "status": "APPROVED", "created_by": self.other.id}, format="json")
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(generated.data["status"], "DRAFT")
        proposal = OpportunityProposal.objects.get()
        self.assertEqual(proposal.created_by, self.owner)

        edited = self.client.patch(self.base + "proposal/", {"version": "CONSULTATIVE", "understanding": "Texto revisado pelo humano", "status": "APPROVED"}, format="json")
        self.assertEqual(edited.data["understanding"], "Texto revisado pelo humano")
        self.assertEqual(edited.data["status"], "DRAFT")
        approved = self.client.post(self.base + "proposal/approve/", {"version": "CONSULTATIVE"}, format="json")
        self.assertEqual(approved.data["status"], "APPROVED")
        self.assertIsNotNone(approved.data["approved_at"])

    @patch("professional.views.generate_opportunity_proposal", return_value=(VALID_PROPOSAL, "gemini", "safe-model"))
    def test_regeneration_never_erases_approved_human_version(self, generate):
        analysis = OpportunityAnalysis.objects.create(opportunity=self.opportunity, created_by=self.owner, ai_provider="test", **VALID_ANALYSIS)
        OpportunityProposal.objects.create(opportunity=self.opportunity, created_by=self.owner, version="SHORT", status="APPROVED", understanding="Edição humana", ai_provider="test", **{key: value for key, value in VALID_PROPOSAL.items() if key != "understanding"})
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.base + "generate-proposal/", {"version": "SHORT"}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(OpportunityProposal.objects.get().understanding, "Edição humana")
        generate.assert_not_called()

    @patch("professional.views.generate_opportunity_execution_plan", return_value=(VALID_PLAN, "gemini", "safe-model"))
    def test_execution_plan_requires_approved_proposal_and_persists(self, generate):
        proposal = OpportunityProposal.objects.create(opportunity=self.opportunity, created_by=self.owner, version="TECHNICAL", ai_provider="test", **VALID_PROPOSAL)
        self.client.force_authenticate(self.owner)
        blocked = self.client.post(self.base + "generate-execution-plan/", {"proposal_version": "TECHNICAL"}, format="json")
        self.assertEqual(blocked.status_code, 409)
        proposal.status = "APPROVED"
        proposal.save(update_fields=["status"])
        response = self.client.post(self.base + "generate-execution-plan/", {"proposal_version": "TECHNICAL"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertTrue(OpportunityExecutionPlan.objects.filter(opportunity=self.opportunity).exists())
        self.assertEqual(self.client.get(self.base + "execution-plan/").status_code, 200)
        self.assertEqual(generate.call_count, 1)
