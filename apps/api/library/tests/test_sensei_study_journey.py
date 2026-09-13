from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import (
    SenseiCompetency,
    SenseiCompetencyEvidence,
    SenseiCompetencyProgress,
    SenseiFormation,
    SenseiFormationModule,
    SenseiProgress,
    SenseiStudyJourney,
    SenseiStudyUnit,
    SenseiUnitStudyProgress,
)


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class SenseiStudyJourneyApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.sensei = users.objects.create_user(
            email="journey@example.com", username="journey", password="test", is_staff=True
        )
        self.other_sensei = users.objects.create_user(
            email="other-journey@example.com", username="other-journey", password="test", is_staff=True
        )
        self.student = users.objects.create_user(
            email="journey-student@example.com", username="journey-student", password="test"
        )
        self.formation = SenseiFormation.objects.create(
            title="Jornada de teste",
            slug="jornada-de-estudo-test",
            objective="Estudar sem conceder domínio",
            status=SenseiFormation.Status.ACTIVE,
            created_by=self.sensei,
        )
        self.module = SenseiFormationModule.objects.create(
            formation=self.formation, title="Módulo 1", order=0
        )
        self.first_unit = SenseiStudyUnit.objects.create(
            module=self.module,
            title="Primeira unidade",
            objective="Começar pela base",
            order=0,
            status=SenseiStudyUnit.Status.ACTIVE,
        )
        self.second_unit = SenseiStudyUnit.objects.create(
            module=self.module,
            title="Segunda unidade",
            objective="Continuar a progressão",
            order=1,
            status=SenseiStudyUnit.Status.ACTIVE,
        )
        self.competency = SenseiCompetency.objects.create(
            formation=self.formation,
            module=self.module,
            title="Competência sem domínio automático",
            expected_level=3,
            mastery_criteria=["Implementa"],
            order=0,
        )
        self.client.force_authenticate(self.sensei)

    def request(self, method, url, data=None):
        return getattr(self.client, method)(
            url, data=data, format="json" if data is not None else None, REMOTE_ADDR="127.0.0.1"
        )

    @property
    def journey_url(self):
        return reverse("library-sensei-study-journey", kwargs={"formation_pk": self.formation.pk})

    def test_not_started_then_start_formation_is_idempotent(self):
        initial = self.request("get", self.journey_url)
        self.assertEqual(initial.status_code, status.HTTP_200_OK)
        self.assertEqual(initial.data["status"], "NOT_STARTED")
        self.assertEqual(initial.data["current_unit"]["id"], self.first_unit.id)
        self.assertFalse(SenseiStudyJourney.objects.filter(formation=self.formation, user=self.sensei).exists())

        started = self.request("post", self.journey_url)
        self.assertEqual(started.status_code, status.HTTP_201_CREATED)
        self.assertEqual(started.data["status"], "IN_PROGRESS")
        self.assertEqual(started.data["current_unit"]["id"], self.first_unit.id)
        self.assertIsNotNone(started.data["started_at"])
        original_started_at = started.data["started_at"]

        repeated = self.request("post", self.journey_url)
        self.assertEqual(repeated.status_code, status.HTTP_200_OK)
        self.assertEqual(repeated.data["started_at"], original_started_at)
        self.assertEqual(SenseiStudyJourney.objects.filter(formation=self.formation, user=self.sensei).count(), 1)
        self.assertFalse(SenseiUnitStudyProgress.objects.filter(user=self.sensei).exists())

    def test_start_unit_continue_position_refresh_and_login_persistence(self):
        self.request("post", self.journey_url)
        start_url = reverse("library-sensei-unit-start-study", kwargs={"pk": self.first_unit.pk})
        started = self.request("post", start_url)
        self.assertEqual(started.status_code, status.HTTP_201_CREATED)
        self.assertEqual(started.data["study_progress"]["status"], "STUDYING")
        unit_started_at = started.data["study_progress"]["started_at"]

        position = {"section": "practices", "item": 2, "scroll_offset": 480}
        saved = self.request("patch", self.journey_url, {"last_position": position})
        self.assertEqual(saved.status_code, status.HTTP_200_OK)
        self.assertEqual(saved.data["last_position"], position)

        # Refresh and a new authenticated session both recover backend state.
        refreshed = self.request("get", self.journey_url)
        self.assertEqual(refreshed.data["current_unit"]["id"], self.first_unit.id)
        self.assertEqual(refreshed.data["last_position"], position)
        self.client.force_authenticate(user=None)
        self.client.force_authenticate(self.sensei)
        continued = self.request("get", self.journey_url)
        self.assertEqual(continued.data["current_unit"]["id"], self.first_unit.id)
        self.assertEqual(continued.data["last_position"], position)

        repeated = self.request("post", start_url)
        self.assertEqual(repeated.status_code, status.HTTP_200_OK)
        self.assertEqual(repeated.data["study_progress"]["started_at"], unit_started_at)
        self.assertEqual(SenseiUnitStudyProgress.objects.filter(unit=self.first_unit, user=self.sensei).count(), 1)

    def test_continue_returns_unit_in_progress_and_resets_position_when_unit_changes(self):
        self.request("post", reverse("library-sensei-unit-start-study", kwargs={"pk": self.first_unit.pk}))
        self.request("patch", self.journey_url, {"last_position": {"section": "notes"}})
        moved = self.request("post", reverse("library-sensei-unit-start-study", kwargs={"pk": self.second_unit.pk}))
        self.assertEqual(moved.data["journey"]["current_unit"]["id"], self.second_unit.id)
        self.assertEqual(moved.data["journey"]["last_position"], {})
        continued = self.request("get", self.journey_url)
        self.assertEqual(continued.data["current_unit"]["id"], self.second_unit.id)

    def test_study_never_creates_mastery_progress_or_evidence(self):
        self.request("post", self.journey_url)
        self.request("post", reverse("library-sensei-unit-start-study", kwargs={"pk": self.first_unit.pk}))

        self.assertFalse(SenseiCompetencyProgress.objects.filter(competency=self.competency, user=self.sensei).exists())
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency=self.competency).exists())
        self.assertFalse(SenseiProgress.objects.filter(formation=self.formation, user=self.sensei).exists())

        domain = self.request(
            "get", reverse("library-sensei-formation-progress", kwargs={"formation_pk": self.formation.pk})
        )
        self.assertEqual(domain.data["percentage"], "0.00")
        self.assertEqual(domain.data["state"], "NOT_STARTED")

    def test_authorization_local_only_and_private_isolation(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.request("get", self.journey_url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.other_sensei)
        self.assertEqual(self.request("get", self.journey_url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.sensei)
        self.assertEqual(
            self.client.get(self.journey_url, REMOTE_ADDR="198.51.100.10").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_invalid_last_position_and_formation_without_active_unit(self):
        self.request("post", self.journey_url)
        invalid = self.request("patch", self.journey_url, {"last_position": ["not", "structured"]})
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        empty = SenseiFormation.objects.create(
            title="Sem unidades", slug="sem-unidades-ativas", objective="Testar conflito", created_by=self.sensei
        )
        response = self.request(
            "post", reverse("library-sensei-study-journey", kwargs={"formation_pk": empty.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
