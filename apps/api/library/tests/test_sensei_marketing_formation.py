import importlib

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import (
    SenseiCompetencyEvidence, SenseiCompetencyProgress, SenseiFormation,
    SenseiLearningActivity, SenseiLearningAttempt, SenseiProgress,
    SenseiStudyJourney, SenseiUnitSource,
)


AI_SLUG = "engenharia-ia-arquitetura-sistemas-inteligentes"
MARKETING_SLUG = "marketing-digital-performance-gestao-trafego-pago"


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class SenseiMarketingFormationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="marketing@example.com", username="marketing", password="test", is_staff=True)
        self.client.force_authenticate(self.user)
        self.ai = SenseiFormation.objects.get(slug=AI_SLUG)
        self.marketing = SenseiFormation.objects.get(slug=MARKETING_SLUG)

    def request(self, method, url, data=None):
        return getattr(self.client, method)(url, data=data, format="json" if data is not None else None, REMOTE_ADDR="127.0.0.1")

    def test_both_formations_exist_and_marketing_curriculum_has_expected_shape(self):
        self.assertEqual(self.marketing.title, "Marketing Digital, Performance e Gestão de Tráfego Pago")
        self.assertEqual(self.marketing.modules.count(), 16)
        self.assertEqual(list(self.marketing.modules.order_by("order").values_list("order", flat=True)), list(range(16)))
        self.assertEqual(sum(module.study_units.count() for module in self.marketing.modules.all()), 49)
        self.assertEqual(self.marketing.competencies.count(), 32)
        self.assertEqual(set(self.marketing.competencies.values_list("expected_level", flat=True)), {4, 5, 6})
        for module in self.marketing.modules.prefetch_related("study_units", "competencies"):
            self.assertEqual(list(module.study_units.order_by("order").values_list("order", flat=True)), list(range(module.study_units.count())))
            for unit in module.study_units.all():
                self.assertTrue(unit.objective)
                self.assertTrue(unit.study_plan.related_competencies.exists())
                self.assertFalse(unit.curated_sources.exists())
                self.assertEqual(unit.source_gap.status, "OPEN")

    def test_seed_is_idempotent_and_does_not_change_formation_001(self):
        before = (self.ai.modules.count(), self.ai.competencies.count(), sum(module.study_units.count() for module in self.ai.modules.all()))
        migration = importlib.import_module("library.migrations.0022_seed_sensei_marketing_formation")
        migration.seed_marketing_formation(django_apps, None)
        migration.seed_marketing_formation(django_apps, None)
        self.marketing.refresh_from_db()
        self.assertEqual(self.marketing.modules.count(), 16)
        self.assertEqual(self.marketing.competencies.count(), 32)
        self.assertEqual(sum(module.study_units.count() for module in self.marketing.modules.all()), 49)
        self.assertEqual((self.ai.modules.count(), self.ai.competencies.count(), sum(module.study_units.count() for module in self.ai.modules.all())), before)

    def test_initial_state_has_zero_progress_and_no_artificial_mastery_or_evidence(self):
        response = self.request("get", reverse("library-sensei-formation-progress", kwargs={"formation_pk": self.marketing.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["percentage"]), "0.00")
        self.assertEqual(response.data["state"], "NOT_STARTED")
        self.assertFalse(SenseiCompetencyProgress.objects.filter(competency__formation=self.marketing).exists())
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency__formation=self.marketing).exists())

    def test_progress_journey_sources_activities_and_attempts_are_isolated(self):
        ai_unit = self.ai.modules.get(order=0).study_units.get(order=0)
        marketing_unit = self.marketing.modules.get(order=0).study_units.get(order=0)
        ai_competency = self.ai.competencies.order_by("order", "id").first()
        marketing_competency = marketing_unit.study_plan.related_competencies.first()
        SenseiProgress.objects.create(formation=self.ai, user=self.user, percentage=25, state="IN_PROGRESS")
        self.request("post", reverse("library-sensei-study-journey", kwargs={"formation_pk": self.marketing.pk}), {})
        self.assertFalse(SenseiStudyJourney.objects.filter(formation=self.ai, user=self.user).exists())
        self.assertEqual(SenseiStudyJourney.objects.get(formation=self.marketing, user=self.user).current_unit, marketing_unit)
        ai_activity = SenseiLearningActivity.objects.create(user=self.user, unit=ai_unit, competency=ai_competency, activity_type="OWN_WORDS", prompt="IA", difficulty_level=1)
        marketing_activity = SenseiLearningActivity.objects.create(user=self.user, unit=marketing_unit, competency=marketing_competency, activity_type="OWN_WORDS", prompt="Marketing", difficulty_level=1)
        SenseiLearningAttempt.objects.create(activity=ai_activity, user=self.user, attempt_number=1, answer="A", feedback="F", outcome="DEEPEN")
        SenseiLearningAttempt.objects.create(activity=marketing_activity, user=self.user, attempt_number=1, answer="M", feedback="FM", outcome="RETRY")
        activities = self.request("get", reverse("library-sensei-learning-activities", kwargs={"unit_pk": marketing_unit.pk})).data
        self.assertEqual([item["id"] for item in activities], [marketing_activity.id])
        self.assertEqual(activities[0]["attempts"][0]["answer"], "M")
        self.assertFalse(SenseiUnitSource.objects.filter(unit__module__formation=self.marketing).exists())

    def test_formation_api_lists_both_without_crossing_modules(self):
        formations = self.request("get", reverse("library-sensei-formations")).data
        slugs = {item["slug"] for item in formations}
        self.assertTrue({AI_SLUG, MARKETING_SLUG}.issubset(slugs))
        modules = self.request("get", reverse("library-sensei-formation-modules", kwargs={"formation_pk": self.marketing.pk})).data
        self.assertEqual(len(modules), 16)
        self.assertTrue(all(module["title"] != "Fundamentos matemáticos e computacionais" for module in modules))
