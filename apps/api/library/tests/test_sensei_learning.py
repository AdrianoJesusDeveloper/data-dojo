import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ai.services import AIProviderError
from library.models import (
    SenseiCompetency, SenseiCompetencyEvidence, SenseiCompetencyProgress, SenseiFormation,
    SenseiFormationModule, SenseiLearningActivity, SenseiLearningAttempt,
    SenseiLearningProviderPreference, SenseiStudyUnit, SenseiUnitSource,
    SenseiUnitStudyPlan,
)


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class SenseiLearningApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="learning@example.com", username="learning", password="test", is_staff=True)
        self.other = get_user_model().objects.create_user(email="other-learning@example.com", username="other-learning", password="test", is_staff=True)
        self.client.force_authenticate(self.user)
        self.formation = SenseiFormation.objects.get(slug="engenharia-ia-arquitetura-sistemas-inteligentes")
        self.unit = self.formation.modules.get(order=0).study_units.get(order=0)
        self.competency = self.unit.study_plan.related_competencies.order_by("order").first()
        SenseiUnitSource.objects.filter(unit=self.unit).delete()
        for title, editorial_status in (("Fonte aprovada", "APPROVED"), ("Fonte proposta", "PROPOSED"), ("Fonte rejeitada", "REJECTED")):
            SenseiUnitSource.objects.create(unit=self.unit, category="FOUNDATIONAL", source_type="TECHNICAL_BOOK", title=title, objective="Fundamentar", priority=1, editorial_status=editorial_status)

    def request(self, method, url, data=None):
        return getattr(self.client, method)(url, data=data, format="json" if data is not None else None, REMOTE_ADDR="127.0.0.1")

    @property
    def list_url(self):
        return reverse("library-sensei-learning-activities", kwargs={"unit_pk": self.unit.pk})

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "SENSEI_AI_PROVIDER": "groq"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider")
    def test_generation_uses_competency_and_only_approved_sources(self, provider):
        provider.return_value = json.dumps({"activity_type": "CONCEPTUAL_QUESTION", "prompt": "Explique mutabilidade com um exemplo próprio."})
        response = self.request("post", self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        activity = SenseiLearningActivity.objects.get(pk=response.data["id"])
        self.assertEqual(activity.competency, self.competency)
        self.assertEqual(activity.state, "GENERATED")
        source_titles = [source["title"] for source in activity.pedagogical_context["approved_sources"]]
        self.assertEqual(source_titles, ["Fonte aprovada"])
        prompt_context = provider.call_args.args[1][1]["content"]
        self.assertIn("Fonte aprovada", prompt_context)
        self.assertNotIn("Fonte proposta", prompt_context)
        self.assertNotIn("Fonte rejeitada", prompt_context)

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "SENSEI_AI_PROVIDER": "groq"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider")
    def test_multiple_attempts_preserve_history_without_mastery_or_evidence(self, provider):
        provider.side_effect = [
            json.dumps({"activity_type": "DEBUGGING", "prompt": "Encontre o erro."}),
            json.dumps({"feedback": "Teste também uma entrada vazia.", "gap_type": "caso-limite", "outcome": "RETRY", "next_activity_suggestion": "Adicione um teste."}),
            json.dumps({"feedback": "Houve evolução: agora a entrada vazia está coberta.", "gap_type": "", "outcome": "EVIDENCE_CANDIDATE", "next_activity_suggestion": "Defenda sua escolha."}),
        ]
        created = self.request("post", self.list_url, {})
        answer_url = reverse("library-sensei-learning-answer", kwargs={"pk": created.data["id"]})
        first = self.request("post", answer_url, {"response": "O erro está na mutação da lista."})
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        second = self.request("post", answer_url, {"response": "Corrigi a mutação e incluí o caso vazio."})
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        activity = SenseiLearningActivity.objects.get(pk=created.data["id"])
        self.assertEqual(activity.state, "REVIEWED")
        attempts = list(activity.attempts.all())
        self.assertEqual([item.attempt_number for item in attempts], [1, 2])
        self.assertEqual(attempts[0].answer, "O erro está na mutação da lista.")
        self.assertEqual(attempts[0].outcome, "RETRY")
        self.assertEqual(attempts[1].answer, "Corrigi a mutação e incluí o caso vazio.")
        self.assertEqual(attempts[1].outcome, "EVIDENCE_CANDIDATE")
        self.assertEqual([item["attempt_number"] for item in second.data["attempts"]], [1, 2])
        evaluation_payload = provider.call_args.args[1][1]["content"]
        self.assertIn("O erro está na mutação da lista.", evaluation_payload)
        self.assertIn("Teste também uma entrada vazia.", evaluation_payload)
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(submitted_by=self.user).exists())
        self.assertFalse(SenseiCompetencyProgress.objects.filter(user=self.user).exists())
        self.assertEqual(provider.call_count, 3)

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "SENSEI_AI_PROVIDER": "groq"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider", side_effect=AIProviderError("unavailable", "test"))
    def test_provider_failure_is_safe_and_does_not_persist(self, provider):
        response = self.request("post", self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(SenseiLearningActivity.objects.filter(user=self.user).exists())

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "groq-test-model", "SENSEI_AI_PROVIDER": "groq"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider")
    def test_activity_records_effective_provider_and_model_without_fallback(self, provider):
        provider.return_value = json.dumps({"activity_type": "CONCEPTUAL_QUESTION", "prompt": "Explique."})
        response = self.request("post", self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        activity = SenseiLearningActivity.objects.get(pk=response.data["id"])
        self.assertEqual((activity.ai_provider, activity.ai_model), ("groq", "groq-test-model"))
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(provider.call_args.args[0], "groq")

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "groq-test-model", "SENSEI_AI_PROVIDER": "groq"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider")
    def test_attempt_records_provider_selected_for_current_formation(self, provider):
        provider.side_effect = [
            json.dumps({"activity_type": "OWN_WORDS", "prompt": "Explique."}),
            json.dumps({"feedback": "Continue.", "gap_type": "", "outcome": "RETRY", "next_activity_suggestion": "Tente novamente."}),
        ]
        created = self.request("post", self.list_url, {})
        answered = self.request("post", reverse("library-sensei-learning-answer", kwargs={"pk": created.data["id"]}), {"response": "Minha resposta"})
        self.assertEqual(answered.status_code, status.HTTP_200_OK, answered.data)
        attempt = SenseiLearningAttempt.objects.get(activity_id=created.data["id"])
        self.assertEqual((attempt.ai_provider, attempt.ai_model), ("groq", "groq-test-model"))

    def test_provider_preference_endpoint_is_safe_and_formation_scoped(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "SENSEI_AI_PROVIDER": "groq"}, clear=False):
            url = reverse("library-sensei-learning-providers", kwargs={"formation_pk": self.formation.pk})
            listed = self.request("get", url)
            self.assertEqual(listed.status_code, status.HTTP_200_OK)
            self.assertIn({"id": "groq", "label": "Groq", "available": True}, listed.data["providers"])
            self.assertNotIn("API_KEY", str(listed.data))
            stored = self.request("put", url, {"provider": "groq"})
            self.assertEqual(stored.status_code, status.HTTP_200_OK, stored.data)
            self.assertEqual(SenseiLearningProviderPreference.objects.get(user=self.user, formation=self.formation).provider, "groq")
            other_formation = SenseiFormation.objects.create(title="Outra", slug="outra-provider", description="", objective="", status="DRAFT", level="Progressivo")
            other_url = reverse("library-sensei-learning-providers", kwargs={"formation_pk": other_formation.pk})
            self.assertNotEqual(self.request("get", other_url).data["selection_source"], "preference")

    def test_unavailable_provider_is_not_listed_or_persisted(self):
        empty_providers = {"SENSEI_AI_PROVIDER": "groq", "AI_DEFAULT_PROVIDER": "", "OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "DEEPSEEK_API_KEY": "", "GROQ_API_KEY": "", "COPILOT_API_URL": "", "COPILOT_API_TOKEN": ""}
        with patch.dict("os.environ", empty_providers, clear=False):
            url = reverse("library-sensei-learning-providers", kwargs={"formation_pk": self.formation.pk})
            self.assertEqual(self.request("get", url).data["providers"], [])
            self.assertEqual(self.request("put", url, {"provider": "groq"}).status_code, status.HTTP_400_BAD_REQUEST)

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "SENSEI_AI_PROVIDER": "groq"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider")
    def test_valid_unit_in_formation_002_can_generate(self, provider):
        provider.return_value = json.dumps({"activity_type": "PRACTICAL_CHALLENGE", "prompt": "Diagnostique uma campanha."})
        marketing, _ = SenseiFormation.objects.get_or_create(slug="marketing-digital-performance-gestao-de-trafego-pago", defaults={"title": "Marketing", "description": "", "objective": "", "status": "DRAFT", "level": "Progressivo"})
        module, _ = SenseiFormationModule.objects.get_or_create(formation=marketing, order=0, defaults={"title": "Marketing", "description": ""})
        unit, _ = SenseiStudyUnit.objects.get_or_create(module=module, order=0, defaults={"title": "Unidade de Marketing", "objective": "Diagnosticar", "status": "ACTIVE"})
        competency, _ = SenseiCompetency.objects.get_or_create(formation=marketing, module=module, order=0, defaults={"title": "Diagnosticar marketing", "expected_level": 4, "mastery_criteria": ["Diagnostica"]})
        plan, _ = SenseiUnitStudyPlan.objects.get_or_create(unit=unit, defaults={"learning_objectives": ["Diagnosticar"], "practices": ["Praticar"], "expected_evidence": ["Resposta"], "completion_criteria": ["Justificar"]})
        plan.related_competencies.add(competency)
        response = self.request("post", reverse("library-sensei-learning-activities", kwargs={"unit_pk": unit.pk}), {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(SenseiLearningActivity.objects.get(pk=response.data["id"]).unit_id, unit.pk)

    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key", "SENSEI_AI_PROVIDER": "groq"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider")
    def test_valid_generic_formation_unit_can_generate(self, provider):
        provider.return_value = json.dumps({"activity_type": "OWN_WORDS", "prompt": "Explique o conceito."})
        formation = SenseiFormation.objects.create(title="Genérica", slug="generica-learning", description="", objective="", status="DRAFT", level="Progressivo")
        module = SenseiFormationModule.objects.create(formation=formation, title="Base", order=0)
        unit = SenseiStudyUnit.objects.create(module=module, title="Unidade genérica", objective="Explicar", order=0, status="ACTIVE")
        competency = SenseiCompetency.objects.create(formation=formation, module=module, title="Explicar conceito", expected_level=2, mastery_criteria=["Explica"])
        plan = SenseiUnitStudyPlan.objects.create(unit=unit, learning_objectives=["Explicar"], practices=["Praticar"], expected_evidence=["Resposta"], completion_criteria=["Justificar"])
        plan.related_competencies.add(competency)
        response = self.request("post", reverse("library-sensei-learning-activities", kwargs={"unit_pk": unit.pk}), {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    @patch("library.services.sensei_learning.chat_with_provider", side_effect=AIProviderError("unavailable", "test"))
    def test_feedback_provider_failure_does_not_create_partial_attempt(self, provider):
        activity = SenseiLearningActivity.objects.create(user=self.user, unit=self.unit, competency=self.competency, activity_type="OWN_WORDS", prompt="Explique", difficulty_level=1)
        url = reverse("library-sensei-learning-answer", kwargs={"pk": activity.pk})
        response = self.request("post", url, {"response": "Tentativa que não pode ser avaliada"})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(SenseiLearningAttempt.objects.filter(activity=activity).exists())
        activity.refresh_from_db()
        self.assertEqual(activity.state, "GENERATED")

    def test_activity_is_private_and_missing_context_is_rejected(self):
        activity = SenseiLearningActivity.objects.create(user=self.other, unit=self.unit, competency=self.competency, activity_type="OWN_WORDS", prompt="Privada", difficulty_level=1)
        self.assertEqual(self.request("post", reverse("library-sensei-learning-answer", kwargs={"pk": activity.pk}), {"response": "x"}).status_code, status.HTTP_404_NOT_FOUND)
        other_unit = self.formation.modules.get(order=0).study_units.get(order=1)
        url = reverse("library-sensei-learning-activities", kwargs={"unit_pk": other_unit.pk})
        self.assertEqual(self.request("post", url, {}).status_code, status.HTTP_409_CONFLICT)

    def test_non_staff_has_no_permission(self):
        student = get_user_model().objects.create_user(email="student-learning@example.com", username="student-learning", password="test")
        self.client.force_authenticate(student)
        self.assertEqual(self.request("get", self.list_url).status_code, status.HTTP_403_FORBIDDEN)
