import json
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import (
    DidacticLesson, DidacticLessonSection, SenseiCompetency, SenseiCompetencyEvidence,
    SenseiCompetencyProgress, SenseiFormation, SenseiFormationModule, SenseiLearningActivity,
    SenseiLearningAttempt, SenseiStudyUnit, SenseiUnitStudyPlan,
)


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class AuthorshipChallengeApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(email="author-a@example.com", username="author-a", password="test", is_staff=True)
        self.other = users.objects.create_user(email="author-b@example.com", username="author-b", password="test", is_staff=True)
        self.client.force_authenticate(self.user)
        self.formation = SenseiFormation.objects.create(title="Formação autoria", slug="authorship-formation", description="", objective="Aprender", status="DRAFT", level="Progressivo")
        self.module = SenseiFormationModule.objects.create(formation=self.formation, title="Módulo", order=0)
        self.unit = SenseiStudyUnit.objects.create(module=self.module, title="Unidade", objective="Produzir", order=0, status="ACTIVE")
        self.competency = SenseiCompetency.objects.create(formation=self.formation, module=self.module, title="Explicar decisões", expected_level=4, mastery_criteria=["Explica"])
        plan = SenseiUnitStudyPlan.objects.create(unit=self.unit, learning_objectives=["Explicar"], practices=["Praticar"], expected_evidence=["Artefato"], completion_criteria=["Justificar"])
        plan.related_competencies.add(self.competency)
        content_type = ContentType.objects.get_for_model(self.unit)
        self.lesson = DidacticLesson.objects.create(title="Aula", audience="SENSEI", status="DRAFT", source_mode="APPROVED_SOURCES", learning_target_type=content_type, learning_target_id=self.unit.id, author=self.user)
        self.section = DidacticLessonSection.objects.create(lesson=self.lesson, section_type="AUTHORSHIP_CHALLENGE", title="Desafio de Autoria", content="Defenda sua decisão e entregue um artefato.", order=0)
        self.url = reverse("library-sensei-unit-authorship-challenge", kwargs={"pk": self.unit.pk})

    def start(self):
        return self.client.post(self.url, {}, format="json", REMOTE_ADDR="127.0.0.1")

    @patch.dict(os.environ, {"SENSEI_AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key", "GROQ_MODEL": "author-model"}, clear=False)
    @patch("library.services.sensei_learning.chat_with_provider")
    def test_challenge_is_available_for_both_source_modes_and_feedback_is_append_only(self, provider):
        provider.return_value = json.dumps({"feedback": "Boa defesa; explicite o trade-off.", "gap_type": "trade-off", "outcome": "RETRY", "next_activity_suggestion": "Compare alternativas."})
        for source_mode in (DidacticLesson.SourceMode.APPROVED_SOURCES, DidacticLesson.SourceMode.AI_GENERATED_UNSOURCED):
            with self.subTest(source_mode=source_mode):
                SenseiLearningActivity.objects.filter(user=self.user).delete()
                self.lesson.source_mode = source_mode
                self.lesson.save(update_fields=["source_mode"])
                response = self.start()
                self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
                activity_id = response.data["activity"]["id"]
                answer_url = reverse("library-sensei-learning-answer", kwargs={"pk": activity_id})
                first = self.client.post(answer_url, {"response": "Minha primeira defesa."}, format="json", REMOTE_ADDR="127.0.0.1")
                second = self.client.post(answer_url, {"response": "Minha defesa revisada."}, format="json", REMOTE_ADDR="127.0.0.1")
                self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
                self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
                attempts = list(SenseiLearningAttempt.objects.filter(activity_id=activity_id))
                self.assertEqual([attempt.answer for attempt in attempts], ["Minha primeira defesa.", "Minha defesa revisada."])
                self.assertTrue(all(attempt.feedback for attempt in attempts))
                self.assertTrue(all(attempt.ai_provider == "groq" and attempt.ai_model == "author-model" for attempt in attempts))
                self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency=self.competency, validation_status="VALIDATED").exists())
                self.assertFalse(SenseiCompetencyProgress.objects.filter(competency=self.competency).exists())

    def test_missing_challenge_section_cannot_be_started(self):
        self.section.delete()
        concept = DidacticLessonSection.objects.create(lesson=self.lesson, section_type="CONCEPT", title="Conceito", content="Base", order=0)
        response = self.start()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIsNone(response.data.get("activity"))
        self.assertFalse(SenseiLearningActivity.objects.filter(user=self.user).exists())
        concept.delete()

    def test_user_isolation_applies_to_activity_and_attempts(self):
        started = self.start()
        activity_id = started.data["activity"]["id"]
        answer_url = reverse("library-sensei-learning-answer", kwargs={"pk": activity_id})
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url, REMOTE_ADDR="127.0.0.1").data["activity"], None)
        forbidden_attempt = self.client.post(answer_url, {"response": "Resposta alheia"}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(forbidden_attempt.status_code, status.HTTP_404_NOT_FOUND)
