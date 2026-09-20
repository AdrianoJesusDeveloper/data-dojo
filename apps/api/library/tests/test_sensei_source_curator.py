from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import (
    LibrarySource, SenseiCompetencyEvidence, SenseiCompetencyProgress,
    SenseiFormation, SenseiFormationModule, SenseiStudyUnit, SenseiUnitSource,
    SenseiUnitSourceGap, SenseiUnitStudyPlan,
)


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class SenseiSourceCuratorTests(APITestCase):
    def setUp(self):
        users = get_user_model().objects
        self.admin = users.create_user(email="curator@example.com", username="curator", password="test", is_staff=True)
        self.other = users.create_user(email="other-curator@example.com", username="other-curator", password="test", is_staff=True)
        self.student = users.create_user(email="student-curator@example.com", username="student-curator", password="test")
        self.client.force_authenticate(self.admin)
        self.formation = SenseiFormation.objects.create(title="Curadoria", slug="curadoria-test", objective="Curar", created_by=self.admin)
        self.module = SenseiFormationModule.objects.create(formation=self.formation, title="Módulo", order=0)
        self.unit = SenseiStudyUnit.objects.create(module=self.module, title="Unidade", objective="Estudar", order=0, status="ACTIVE")
        SenseiUnitStudyPlan.objects.create(unit=self.unit, learning_objectives=["Compreender"], practices=[], expected_evidence=[], completion_criteria=[])
        self.source = LibrarySource.objects.create(relative_path="curadoria/fonte.pdf", filename="Fonte.pdf", extension="pdf", status="supported")

    def request(self, method, url, data=None, remote="127.0.0.1"):
        return getattr(self.client, method)(url, data=data, format="json" if data is not None else None, REMOTE_ADDR=remote)

    def proposal(self, title="Fonte proposta", required=True):
        response = self.request("post", reverse("library-sensei-unit-sources", kwargs={"unit_pk": self.unit.pk}), {
            "source": self.source.pk, "category": "FOUNDATIONAL", "source_type": "TECHNICAL_BOOK",
            "title": title, "reference": "Edição identificada", "location": "Capítulo 2, seção 2.1",
            "objective": "Apoiar a unidade", "priority": 1, "is_required": required,
            "author_or_organization": "Autora Teste", "publication_date": "2025-01-10",
            "accessed_at": "2026-09-03T12:00:00Z", "source_updated_at": "2025-06-01T12:00:00Z",
            "justification": "Cobertura direta e tecnicamente adequada.", "confidence": "0.900",
            "reliability_notes": "Fonte técnica revisada.", "editorial_status": "APPROVED",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["editorial_status"], "PROPOSED")
        return response.data

    def test_only_human_approved_sources_enter_official_plan(self):
        proposal = self.proposal()
        plan_url = reverse("library-sensei-unit-study-plan", kwargs={"pk": self.unit.pk})
        self.assertEqual(self.request("get", plan_url).data["curated_sources"], [])
        rejected = self.request("patch", reverse("library-sensei-unit-source-review", kwargs={"pk": proposal["id"]}), {"editorial_status": "REJECTED", "rejection_reason": "Referência inadequada"})
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        self.assertEqual(self.request("get", plan_url).data["curated_sources"], [])

        rejected_id = proposal["id"]
        second_source = LibrarySource.objects.create(relative_path="curadoria/fonte-2.pdf", filename="Fonte 2.pdf", extension="pdf", status="supported")
        self.source = second_source
        approved = self.proposal("Fonte aprovada", required=False)
        review = self.request("patch", reverse("library-sensei-unit-source-review", kwargs={"pk": approved["id"]}), {"editorial_status": "APPROVED"})
        self.assertEqual(review.status_code, status.HTTP_200_OK, review.data)
        official = self.request("get", plan_url).data["curated_sources"]
        self.assertEqual([item["id"] for item in official], [approved["id"]])
        self.assertNotIn(rejected_id, [item["id"] for item in official])
        stored = SenseiUnitSource.objects.get(pk=approved["id"])
        self.assertEqual(stored.author_or_organization, "Autora Teste")
        self.assertIsNotNone(stored.reviewed_at)
        self.assertEqual(str(stored.confidence), "0.900")

    def test_approval_requires_human_confirmed_location(self):
        proposal = SenseiUnitSource.objects.create(
            unit=self.unit,
            source=self.source,
            category="FOUNDATIONAL",
            source_type="TECHNICAL_BOOK",
            title="Fonte sem localização",
            reference="Edição identificada",
            location="",
            objective="Apoiar a unidade",
            priority=1,
            justification="Cobertura direta e tecnicamente adequada.",
            editorial_status=SenseiUnitSource.EditorialStatus.PROPOSED,
            curated_by=self.admin,
        )
        response = self.request(
            "patch",
            reverse("library-sensei-unit-source-review", kwargs={"pk": proposal.pk}),
            {"editorial_status": "APPROVED"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        proposal.refresh_from_db()
        self.assertEqual(proposal.editorial_status, SenseiUnitSource.EditorialStatus.PROPOSED)

    def test_gap_permissions_and_source_absence_do_not_touch_mastery(self):
        gap = SenseiUnitSourceGap.objects.create(unit=self.unit, reason="NEEDS_SOURCE", requirements=["Paper primário"], created_by=self.admin)
        plan = self.request("get", reverse("library-sensei-unit-study-plan", kwargs={"pk": self.unit.pk})).data
        self.assertEqual(plan["source_gap"]["status"], "OPEN")
        self.assertEqual(plan["curated_sources"], [])
        started = self.request("post", reverse("library-sensei-unit-start-study", kwargs={"pk": self.unit.pk}), {})
        self.assertIn(started.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertFalse(SenseiCompetencyProgress.objects.filter(competency__formation=self.formation).exists())
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency__formation=self.formation).exists())

        self.client.force_authenticate(self.student)
        self.assertEqual(self.request("get", reverse("library-sensei-unit-sources", kwargs={"unit_pk": self.unit.pk})).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.request("get", reverse("library-sensei-unit-source-gap", kwargs={"pk": self.unit.pk}), remote="198.51.100.10").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(SenseiUnitSourceGap.objects.get(pk=gap.pk).status, "OPEN")
