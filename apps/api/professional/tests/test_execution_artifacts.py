from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.test import APITestCase

from library.models import SenseiCompetency, SenseiCompetencyEvidence, SenseiCompetencyProgress, SenseiFormation
from professional.models import Opportunity, OpportunityExecutionArtifact, OpportunityExecutionEvidenceLink
from professional.services import submit_execution_artifacts_as_competency_evidence


class OpportunityExecutionArtifactTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="artifact-owner",
            email="artifact-owner@example.com",
            password="safe-test-pass",
        )
        self.opportunity = Opportunity.objects.create(
            created_by=self.owner,
            title="Automação de processo",
            description="Projeto profissional real",
            source=Opportunity.Source.DIRECT_CLIENT,
            currency="BRL",
        )

    def test_creates_real_execution_artifact_with_private_default(self):
        artifact = OpportunityExecutionArtifact.objects.create(
            opportunity=self.opportunity,
            created_by=self.owner,
            artifact_type=OpportunityExecutionArtifact.ArtifactType.CODE,
            title="Implementação do fluxo principal",
            description="Código criado durante a execução real do projeto.",
            content="Implementação concluída e validada localmente.",
        )

        self.assertEqual(artifact.opportunity, self.opportunity)
        self.assertEqual(artifact.created_by, self.owner)
        self.assertEqual(
            artifact.confidentiality,
            OpportunityExecutionArtifact.Confidentiality.PRIVATE,
        )
        self.assertEqual(
            str(artifact),
            "Código: Implementação do fluxo principal",
        )


class OpportunityExecutionArtifactApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="artifact-api-owner", email="artifact-api-owner@example.com", password="safe-test-pass", is_staff=True,
        )
        self.other = user_model.objects.create_user(
            username="artifact-api-other", email="artifact-api-other@example.com", password="safe-test-pass", is_staff=True,
        )
        self.opportunity = self.create_opportunity(self.owner)
        self.other_opportunity = self.create_opportunity(self.other)
        self.url = self.artifacts_url(self.opportunity)
        self.payload = {
            "artifact_type": OpportunityExecutionArtifact.ArtifactType.CODE,
            "title": "Implementação do fluxo principal",
            "description": "Código criado durante a execução real do projeto.",
            "content": "Implementação concluída.",
        }
        self.client.force_authenticate(self.owner)

    def create_opportunity(self, user):
        return Opportunity.objects.create(
            created_by=user, title="Projeto", description="Projeto profissional real",
            source=Opportunity.Source.DIRECT_CLIENT, currency="BRL",
        )

    def artifacts_url(self, opportunity):
        return f"/api/professional/opportunities/{opportunity.pk}/execution-artifacts/"

    def test_owner_creates_artifact_with_server_ownership_and_private_default(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        artifact = OpportunityExecutionArtifact.objects.get(pk=response.data["id"])
        self.assertEqual(artifact.opportunity, self.opportunity)
        self.assertEqual(artifact.created_by, self.owner)
        for field, value in self.payload.items():
            self.assertEqual(getattr(artifact, field), value)
        self.assertEqual(artifact.confidentiality, OpportunityExecutionArtifact.Confidentiality.PRIVATE)
        self.assertEqual(response.data["opportunity"], self.opportunity.pk)
        self.assertEqual(response.data["created_by"], self.owner.pk)
        self.assertEqual(response.data["confidentiality"], "PRIVATE")

    def test_owner_lists_only_own_artifacts_for_requested_opportunity(self):
        first = OpportunityExecutionArtifact.objects.create(
            opportunity=self.opportunity, created_by=self.owner, **self.payload,
        )
        second = OpportunityExecutionArtifact.objects.create(
            opportunity=self.opportunity, created_by=self.owner, **self.payload,
        )
        OpportunityExecutionArtifact.objects.create(
            opportunity=self.opportunity, created_by=self.other, **self.payload,
        )
        OpportunityExecutionArtifact.objects.create(
            opportunity=self.other_opportunity, created_by=self.other, **self.payload,
        )
        OpportunityExecutionArtifact.objects.create(
            opportunity=self.create_opportunity(self.owner), created_by=self.owner, **self.payload,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [second.pk, first.pk])

    def test_other_users_opportunity_artifacts_are_hidden(self):
        OpportunityExecutionArtifact.objects.create(
            opportunity=self.other_opportunity, created_by=self.other, **self.payload,
        )

        response = self.client.get(self.artifacts_url(self.other_opportunity))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_to_other_users_opportunity_returns_404_without_creating_artifact(self):
        count = OpportunityExecutionArtifact.objects.count()

        response = self.client.post(
            self.artifacts_url(self.other_opportunity), self.payload, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(OpportunityExecutionArtifact.objects.count(), count)

    def test_payload_cannot_forge_opportunity_or_created_by(self):
        response = self.client.post(
            self.url,
            {**self.payload, "opportunity": self.other_opportunity.pk, "created_by": self.other.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        artifact = OpportunityExecutionArtifact.objects.get(pk=response.data["id"])
        self.assertEqual(artifact.opportunity, self.opportunity)
        self.assertEqual(artifact.created_by, self.owner)
        self.assertEqual(response.data["opportunity"], self.opportunity.pk)
        self.assertEqual(response.data["created_by"], self.owner.pk)
        self.assertFalse(OpportunityExecutionArtifact.objects.filter(opportunity=self.other_opportunity).exists())
        self.assertFalse(OpportunityExecutionArtifact.objects.filter(created_by=self.other).exists())


class OpportunityExecutionEvidenceLinkTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="evidence-link-owner",
            email="evidence-link-owner@example.com",
            password="safe-test-pass",
        )
        self.opportunity = Opportunity.objects.create(
            created_by=self.owner,
            title="Projeto real",
            description="Implementação profissional",
            source=Opportunity.Source.DIRECT_CLIENT,
        )
        formation = SenseiFormation.objects.create(
            title="Desenvolvimento", slug="evidence-link-development",
            objective="Implementar soluções",
        )
        self.competency = SenseiCompetency.objects.create(
            formation=formation, title="Implementar uma solução",
            mastery_criteria=["Implementação funcional"],
        )
        self.artifact = self.create_artifact()
        self.evidence = self.create_evidence()

    def create_artifact(self):
        return OpportunityExecutionArtifact.objects.create(
            opportunity=self.opportunity, created_by=self.owner,
            artifact_type=OpportunityExecutionArtifact.ArtifactType.CODE,
            title="Código implementado", description="Trabalho executado no projeto",
        )

    def create_evidence(self):
        return SenseiCompetencyEvidence.objects.create(
            competency=self.competency, submitted_by=self.owner,
            evidence_type=SenseiCompetencyEvidence.EvidenceType.CODE,
            description="Demonstração de implementação",
            demonstrated_level=SenseiCompetency.MasteryLevel.IMPLEMENTS,
        )

    def test_creates_link_between_artifact_and_evidence(self):
        link = OpportunityExecutionEvidenceLink.objects.create(
            artifact=self.artifact, evidence=self.evidence,
        )

        link.refresh_from_db()
        self.assertEqual(link.artifact, self.artifact)
        self.assertEqual(link.evidence, self.evidence)
        self.assertIsNotNone(link.created_at)
        self.assertEqual(str(link), f"{self.artifact.pk} - {self.evidence.pk}")
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.validation_status, SenseiCompetencyEvidence.ValidationStatus.PENDING)

    def test_duplicate_artifact_evidence_pair_is_rejected(self):
        OpportunityExecutionEvidenceLink.objects.create(artifact=self.artifact, evidence=self.evidence)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OpportunityExecutionEvidenceLink.objects.create(artifact=self.artifact, evidence=self.evidence)

        self.assertEqual(OpportunityExecutionEvidenceLink.objects.count(), 1)

    def test_artifact_can_support_two_evidences(self):
        other_evidence = self.create_evidence()
        OpportunityExecutionEvidenceLink.objects.create(artifact=self.artifact, evidence=self.evidence)
        OpportunityExecutionEvidenceLink.objects.create(artifact=self.artifact, evidence=other_evidence)

        self.assertCountEqual(
            self.artifact.evidence_links.values_list("evidence_id", flat=True),
            [self.evidence.pk, other_evidence.pk],
        )

    def test_evidence_can_be_supported_by_two_artifacts(self):
        other_artifact = self.create_artifact()
        OpportunityExecutionEvidenceLink.objects.create(artifact=self.artifact, evidence=self.evidence)
        OpportunityExecutionEvidenceLink.objects.create(artifact=other_artifact, evidence=self.evidence)

        self.assertCountEqual(
            self.evidence.professional_execution_links.values_list("artifact_id", flat=True),
            [self.artifact.pk, other_artifact.pk],
        )


class ExecutionEvidenceSubmissionApiTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="bridge-owner", email="bridge-owner@example.com", password="safe-test-pass", is_staff=True,
        )
        self.other = get_user_model().objects.create_user(
            username="bridge-other", email="bridge-other@example.com", password="safe-test-pass", is_staff=True,
        )
        self.opportunity = self.create_opportunity(self.owner)
        self.artifact = self.create_artifact(self.opportunity, self.owner)
        formation = SenseiFormation.objects.create(
            title="Formação", slug="bridge-formation", objective="Implementar", created_by=self.owner,
        )
        self.competency = SenseiCompetency.objects.create(
            formation=formation, title="Implementação", mastery_criteria=["Código funcional"],
        )
        self.payload = {
            "artifact_ids": [self.artifact.pk], "competency": self.competency.pk,
            "evidence_type": "CODE", "demonstrated_level": 3,
            "description": "Implementação real", "content": "Código e explicação",
        }
        self.url = self.submission_url(self.opportunity)
        self.client.force_authenticate(self.owner)

    def create_opportunity(self, user):
        return Opportunity.objects.create(
            created_by=user, title="Projeto", description="Trabalho real", source=Opportunity.Source.DIRECT_CLIENT,
        )

    def create_artifact(self, opportunity, user):
        return OpportunityExecutionArtifact.objects.create(
            opportunity=opportunity, created_by=user, artifact_type="CODE", title="Código", description="Implementação",
        )

    def submission_url(self, opportunity):
        return f"/api/professional/opportunities/{opportunity.pk}/submit-execution-evidence/"

    def assert_no_evidence(self):
        self.assertFalse(SenseiCompetencyEvidence.objects.exists())
        self.assertFalse(OpportunityExecutionEvidenceLink.objects.exists())

    def test_valid_submission_delegates_to_service_and_remains_pending(self):
        progress = SenseiCompetencyProgress.objects.create(competency=self.competency, user=self.owner)
        before = SenseiCompetencyProgress.objects.values().get(pk=progress.pk)
        with patch(
            "professional.views.submit_execution_artifacts_as_competency_evidence",
            wraps=submit_execution_artifacts_as_competency_evidence,
        ) as submit:
            response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        submit.assert_called_once()
        self.assertEqual(submit.call_args.kwargs["user"], self.owner)
        self.assertEqual(submit.call_args.kwargs["artifact_ids"], [self.artifact.pk])
        self.assertEqual(submit.call_args.kwargs["competency"].pk, self.competency.pk)
        evidence = SenseiCompetencyEvidence.objects.get(pk=response.data["id"])
        self.assertEqual(evidence.validation_status, "PENDING")
        self.assertEqual(response.data["validation_status"], "PENDING")
        self.assertIsNone(evidence.validated_by)
        self.assertIsNone(evidence.validated_at)
        self.assertEqual(evidence.professional_execution_links.get().artifact, self.artifact)
        self.artifact.refresh_from_db()
        self.assertEqual(self.artifact.confidentiality, "PRIVATE")
        self.assertEqual(SenseiCompetencyProgress.objects.values().get(pk=progress.pk), before)
        self.assertEqual(SenseiCompetencyProgress.objects.count(), 1)

    def test_two_artifacts_from_same_opportunity(self):
        second = self.create_artifact(self.opportunity, self.owner)
        response = self.client.post(
            self.url, {**self.payload, "artifact_ids": [self.artifact.pk, second.pk]}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertCountEqual(
            OpportunityExecutionEvidenceLink.objects.filter(evidence_id=response.data["id"]).values_list("artifact_id", flat=True),
            [self.artifact.pk, second.pk],
        )

    def test_other_opportunity_artifact_is_rejected_even_for_same_owner(self):
        artifact = self.create_artifact(self.create_opportunity(self.owner), self.owner)
        response = self.client.post(
            self.url, {**self.payload, "artifact_ids": [self.artifact.pk, artifact.pk]}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_no_evidence()

    def test_foreign_and_missing_artifacts_return_same_error(self):
        artifact = self.create_artifact(self.create_opportunity(self.other), self.other)
        foreign = self.client.post(self.url, {**self.payload, "artifact_ids": [artifact.pk]}, format="json")
        missing = self.client.post(self.url, {**self.payload, "artifact_ids": [artifact.pk + 1000]}, format="json")
        self.assertEqual(foreign.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing.status_code, foreign.status_code)
        self.assertEqual(missing.data, foreign.data)
        self.assert_no_evidence()

    def test_foreign_opportunity_is_hidden_before_payload_validation(self):
        response = self.client.post(self.submission_url(self.create_opportunity(self.other)), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assert_no_evidence()

    def test_invalid_payload_returns_400(self):
        for payload in ({}, {**self.payload, "artifact_ids": "invalid"}, {**self.payload, "competency": "invalid"}):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_no_evidence()

    def test_service_domain_validation_errors_remain_400(self):
        for changes in ({"content": ""}, {"evidence_type": "INVALID"}, {"demonstrated_level": 99}, {"artifact_ids": []}):
            with self.subTest(changes=changes):
                with patch(
                    "professional.views.submit_execution_artifacts_as_competency_evidence",
                    wraps=submit_execution_artifacts_as_competency_evidence,
                ) as submit:
                    response = self.client.post(self.url, {**self.payload, **changes}, format="json")
                submit.assert_called_once()
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assert_no_evidence()

    def test_service_rejects_private_competency_of_other_user(self):
        formation = self.competency.formation
        formation.created_by = self.other
        formation.save(update_fields=["created_by"])
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assert_no_evidence()

    def test_endpoint_accepts_only_post(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assert_no_evidence()


class ExecutionArtifactEvidenceSubmissionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="submission-owner", email="submission-owner@example.com", password="safe-test-pass",
        )
        self.other = get_user_model().objects.create_user(
            username="submission-other", email="submission-other@example.com", password="safe-test-pass",
        )
        self.opportunity = Opportunity.objects.create(
            created_by=self.owner, title="Projeto", description="Trabalho real",
            source=Opportunity.Source.DIRECT_CLIENT,
        )
        self.formation = SenseiFormation.objects.create(
            title="Formação", slug="submission-formation", objective="Implementar soluções", created_by=self.owner,
        )
        self.competency = SenseiCompetency.objects.create(
            formation=self.formation, title="Implementação", mastery_criteria=["Código funcional"],
        )
        self.artifact = self.create_artifact()

    def create_artifact(self, **overrides):
        data = {
            "opportunity": self.opportunity, "created_by": self.owner,
            "artifact_type": OpportunityExecutionArtifact.ArtifactType.CODE,
            "title": "Código", "description": "Implementação real",
        }
        data.update(overrides)
        return OpportunityExecutionArtifact.objects.create(**data)

    def submit(self, **overrides):
        data = {
            "user": self.owner, "artifact_ids": [self.artifact.pk], "competency": self.competency,
            "evidence_type": SenseiCompetencyEvidence.EvidenceType.TECHNICAL_DECISION,
            "demonstrated_level": SenseiCompetency.MasteryLevel.JUSTIFIES,
            "description": "Justificativa da solução", "content": "Decisão e suas razões",
        }
        data.update(overrides)
        return submit_execution_artifacts_as_competency_evidence(**data)

    def assert_no_submission(self):
        self.assertFalse(SenseiCompetencyEvidence.objects.exists())
        self.assertFalse(OpportunityExecutionEvidenceLink.objects.exists())

    def test_creates_pending_evidence_and_link_without_changing_private_artifact(self):
        before = OpportunityExecutionArtifact.objects.values().get(pk=self.artifact.pk)
        evidence = self.submit()
        evidence.refresh_from_db()

        self.assertEqual(evidence.validation_status, SenseiCompetencyEvidence.ValidationStatus.PENDING)
        self.assertIsNone(evidence.validated_by)
        self.assertIsNone(evidence.validated_at)
        self.assertEqual(evidence.competency, self.competency)
        self.assertEqual(evidence.submitted_by, self.owner)
        self.assertEqual(evidence.evidence_type, SenseiCompetencyEvidence.EvidenceType.TECHNICAL_DECISION)
        self.assertEqual(evidence.demonstrated_level, SenseiCompetency.MasteryLevel.JUSTIFIES)
        self.assertEqual(evidence.professional_execution_links.get().artifact, self.artifact)
        self.assertEqual(before["confidentiality"], OpportunityExecutionArtifact.Confidentiality.PRIVATE)
        self.assertEqual(OpportunityExecutionArtifact.objects.values().get(pk=self.artifact.pk), before)
        self.assertFalse(SenseiCompetencyProgress.objects.exists())

    def test_two_artifacts_link_to_same_evidence(self):
        second = self.create_artifact()
        evidence = self.submit(artifact_ids=[self.artifact.pk, second.pk])
        self.assertEqual(SenseiCompetencyEvidence.objects.count(), 1)
        self.assertCountEqual(
            evidence.professional_execution_links.values_list("artifact_id", flat=True),
            [self.artifact.pk, second.pk],
        )

    def test_duplicate_ids_create_only_one_link(self):
        evidence = self.submit(artifact_ids=[self.artifact.pk, self.artifact.pk])
        self.assertEqual(evidence.professional_execution_links.count(), 1)

    def test_empty_artifacts_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.submit(artifact_ids=[])
        self.assert_no_submission()

    def test_foreign_and_missing_artifacts_have_same_error(self):
        foreign = self.create_artifact(created_by=self.other)
        missing_id = foreign.pk + 1000
        with self.assertRaises(NotFound) as foreign_error:
            self.submit(artifact_ids=[foreign.pk])
        with self.assertRaises(NotFound) as missing_error:
            self.submit(artifact_ids=[missing_id])
        self.assertEqual(foreign_error.exception.detail, missing_error.exception.detail)
        self.assert_no_submission()

    def test_mixed_ownership_rejects_entire_submission(self):
        foreign = self.create_artifact(created_by=self.other)
        with self.assertRaises(NotFound):
            self.submit(artifact_ids=[self.artifact.pk, foreign.pk])
        self.assert_no_submission()

    def test_artifact_on_foreign_opportunity_is_rejected(self):
        self.opportunity.created_by = self.other
        self.opportunity.save(update_fields=["created_by"])
        with self.assertRaises(NotFound):
            self.submit()
        self.assert_no_submission()

    def test_foreign_private_competency_is_rejected(self):
        self.formation.created_by = self.other
        self.formation.save(update_fields=["created_by"])
        with self.assertRaises(NotFound):
            self.submit()
        self.assert_no_submission()

    def test_global_formation_competency_is_accepted(self):
        self.formation.created_by = None
        self.formation.save(update_fields=["created_by"])
        evidence = self.submit()
        self.assertEqual(evidence.competency, self.competency)

    def test_existing_serializer_rejects_invalid_evidence(self):
        for overrides in (
            {"content": "", "reference_url": ""},
            {"evidence_type": "INVALID"},
            {"demonstrated_level": 99},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValidationError):
                    self.submit(**overrides)
                self.assert_no_submission()

    def test_existing_competency_progress_is_unchanged(self):
        progress = SenseiCompetencyProgress.objects.create(
            competency=self.competency, user=self.owner, current_level=0,
            state=SenseiCompetencyProgress.State.STUDYING,
        )
        before = SenseiCompetencyProgress.objects.values().get(pk=progress.pk)
        self.submit()
        self.assertEqual(SenseiCompetencyProgress.objects.count(), 1)
        self.assertEqual(SenseiCompetencyProgress.objects.values().get(pk=progress.pk), before)

    def test_link_failure_rolls_back_evidence_and_preceding_links(self):
        second = self.create_artifact()
        create_link = OpportunityExecutionEvidenceLink.objects.create

        def fail_second_link(**kwargs):
            if OpportunityExecutionEvidenceLink.objects.exists():
                raise IntegrityError("Link creation failed")
            return create_link(**kwargs)

        with patch(
            "professional.services.OpportunityExecutionEvidenceLink.objects.create",
            side_effect=fail_second_link,
        ):
            with self.assertRaises(IntegrityError):
                self.submit(artifact_ids=[self.artifact.pk, second.pk])
        self.assert_no_submission()
