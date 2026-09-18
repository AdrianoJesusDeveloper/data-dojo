from copy import deepcopy
import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone

from library.models import (
    Book, BookChunk, LibrarySource, SourceCitation, StudioApproval, StudioDossierVersion,
    StudioProject, StudioResearchContext, StudioResearchEvidence,
)
from library.services.studio_dossier import create_dossier_version, transition_dossier_version
from library.services.studio_research import StudioResearchError, build_research_context, research_prompt_context


class StudioDossierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.owner = users.create_user(username="dossier-owner", email="dossier-owner@example.com", is_staff=True)
        cls.other = users.create_user(username="dossier-other", email="dossier-other@example.com", is_staff=True)
        cls.student = users.create_user(username="dossier-student", email="dossier-student@example.com")
        cls.project = StudioProject.objects.create(title="Dossiê", theme="Dados", objective="Consolidar", created_by=cls.owner, research_policy="HYBRID")
        cls.other_project = StudioProject.objects.create(title="Outro", theme="Dados", objective="Outro", created_by=cls.other, research_policy="HYBRID")
        cls.source = LibrarySource.objects.create(relative_path="dossier.pdf", filename="dossier.pdf", extension="pdf", size_bytes=10, sha256="a" * 64)
        cls.book = Book.objects.create(title="Livro", source=cls.source, status="ready", file="books/dossier.pdf")
        cls.chunk = BookChunk.objects.create(book=cls.book, chunk_index=0, page_number=7, content="Conteúdo completo que não deve ser copiado.", embedding=[0.1])
        cls.project.books.add(cls.book)
        cls.context = StudioResearchContext.objects.create(project=cls.project, policy="HYBRID", query="Dados", status="ready", dossier={"thesis": "Pesquisa automática"})
        cls.acervo = StudioResearchEvidence.objects.create(context=cls.context, source_kind="ACERVO", chunk=cls.chunk, title="Livro", query="Dados", excerpt="Trecho " * 300, retrieved_at=timezone.now(), metadata={"private": "not-a-snapshot-field"})
        cls.web = StudioResearchEvidence.objects.create(context=cls.context, source_kind="WEB", title="Documentação", url="https://example.com/docs", domain="example.com", query="Dados", excerpt="Evidência web", retrieved_at=timezone.now())
        cls.gap = StudioResearchEvidence.objects.create(context=cls.context, source_kind="GAP", query="Dados", excerpt="Faltam fontes", retrieved_at=timezone.now())
        cls.citation = SourceCitation.objects.create(project=cls.project, chunk=cls.chunk, source=cls.source, book_title="Livro", page_number=7, excerpt="Citação selecionada")
        other_context = StudioResearchContext.objects.create(project=cls.other_project, policy="HYBRID", query="Outro")
        cls.foreign_evidence = StudioResearchEvidence.objects.create(context=other_context, source_kind="WEB", query="Outro", url="https://example.com/private", retrieved_at=timezone.now())
        cls.foreign_citation = SourceCitation.objects.create(project=cls.other_project, excerpt="Privado")

    def create(self, **kwargs):
        defaults = dict(project_id=self.project.pk, actor=self.owner, content={"executive_summary": "Síntese humana"}, expected_version=0)
        defaults.update(kwargs)
        return create_dossier_version(**defaults)

    def transition(self, dossier, status, **kwargs):
        defaults = dict(project_id=self.project.pk, actor=self.owner, version_id=dossier.pk, expected_version=dossier.version, status=status)
        defaults.update(kwargs)
        return transition_dossier_version(**defaults)

    def test_existing_projects_have_no_implicit_dossier(self):
        self.assertFalse(self.project.dossier_versions.exists())
        self.assertFalse(self.other_project.dossier_versions.exists())

    def test_first_version_is_draft_with_owner_and_schema(self):
        dossier = self.create()
        self.assertEqual((dossier.version, dossier.status, dossier.schema_version), (1, "DRAFT", "master-dossier-v1"))
        self.assertEqual(dossier.created_by, self.owner)
        self.assertEqual(dossier.research_policy, "HYBRID")
        self.assertIsNotNone(dossier.created_at)
        self.assertIsNone(dossier.based_on_id)
        self.assertIsNone(dossier.reviewed_by_id)
        self.assertIsNone(dossier.reviewed_at)

    def test_new_revision_preserves_human_content_and_based_on(self):
        first = self.create(evidence_ids=[self.acervo.pk])
        second = self.create(expected_version=1, content={"executive_summary": "Revisão humana"})
        first.refresh_from_db()
        self.assertEqual(first.content["executive_summary"], "Síntese humana")
        self.assertEqual((second.version, second.based_on_id), (2, first.pk))
        self.assertEqual(second.references_snapshot, first.references_snapshot)

    def test_stale_and_invalid_expected_versions_do_not_write(self):
        self.create()
        for expected in (0, 2, True, None, "1"):
            with self.subTest(expected=expected), self.assertRaises(ValidationError):
                self.create(expected_version=expected)
        self.assertEqual(self.project.dossier_versions.count(), 1)

    def test_same_version_numbers_are_independent_between_projects(self):
        first = self.create()
        other = self.create(project_id=self.other_project.pk, actor=self.other)
        self.assertEqual(first.version, other.version)

    def test_other_owner_student_and_inactive_actor_cannot_write(self):
        for actor in (self.other, self.student, None):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.create(actor=actor)
        self.owner.is_active = False
        with self.assertRaises(PermissionDenied):
            self.create()
        self.assertFalse(self.project.dossier_versions.exists())

    def test_foreign_references_are_rejected(self):
        for kwargs in ({"evidence_ids": [self.foreign_evidence.pk]}, {"citation_ids": [self.foreign_citation.pk]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.create(**kwargs)

    def test_missing_duplicate_and_invalid_reference_ids_are_rejected(self):
        for ids in ([999999], [self.web.pk, self.web.pk], [True], ["1"]):
            with self.subTest(ids=ids), self.assertRaises(ValidationError):
                self.create(evidence_ids=ids)

    def test_snapshot_contains_only_bounded_provenance(self):
        dossier = self.create(evidence_ids=[self.acervo.pk, self.web.pk], citation_ids=[self.citation.pk])
        acervo = next(ref for ref in dossier.references_snapshot if ref["id"] == f"evidence:{self.acervo.pk}")
        self.assertEqual((acervo["chunk_id"], acervo["book_id"], acervo["source_id"], acervo["page_number"]), (self.chunk.pk, self.book.pk, self.source.pk, 7))
        self.assertEqual(len(acervo["excerpt"]), 1500)
        for ref in dossier.references_snapshot:
            self.assertFalse({"metadata", "embedding", "file", "content", "dossier", "relative_path"} & ref.keys())
        citation = next(ref for ref in dossier.references_snapshot if ref.get("citation_id"))
        self.assertIn("recorded_at", citation)
        self.assertNotIn("retrieved_at", citation)

    def test_library_source_deletion_does_not_remove_snapshot(self):
        first = self.create(evidence_ids=[self.acervo.pk])
        snapshot = deepcopy(first.references_snapshot)
        self.book.delete()
        self.source.delete()
        first.refresh_from_db()
        self.assertEqual(first.references_snapshot, snapshot)
        second = self.create(expected_version=1)
        self.assertEqual(second.references_snapshot, snapshot)

    def test_malformed_snapshot_fails_as_validation_error(self):
        from library.dossier_contracts import validate_dossier
        first = self.create(evidence_ids=[self.web.pk])
        for field, value in (("source_kind", []), ("url", "https://["), ("captured_at", "invalid"), ("metadata", {"private": "value"})):
            refs = deepcopy(first.references_snapshot)
            refs[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_dossier({}, refs, "HYBRID", "master-dossier-v1")
        with self.assertRaises(ValidationError):
            validate_dossier({}, [], [], "master-dossier-v1")

    def test_research_rebuild_does_not_overwrite_human_version_or_provenance(self):
        first = self.create(evidence_ids=[self.web.pk], citation_ids=[self.citation.pk])
        snapshot = deepcopy(first.references_snapshot)
        self.project.research_policy = "WEB_ONLY"
        self.project.save(update_fields=["research_policy"])
        provider = Mock()
        provider.search.return_value = []
        build_research_context(self.project, web_provider=provider)
        self.citation.delete()
        first.refresh_from_db()
        self.assertEqual(first.content["executive_summary"], "Síntese humana")
        self.assertEqual(first.references_snapshot, snapshot)
        self.assertFalse(StudioResearchEvidence.objects.filter(pk=self.web.pk).exists())
        self.project.research_policy = "HYBRID"
        self.project.save(update_fields=["research_policy"])
        second = self.create(expected_version=1)
        self.assertEqual(second.references_snapshot, snapshot)

    def test_policy_rejects_forbidden_origins(self):
        for policy, evidence in (("ACERVO_ONLY", self.web), ("WEB_ONLY", self.acervo)):
            self.project.research_policy = policy
            self.project.save(update_fields=["research_policy"])
            with self.subTest(policy=policy), self.assertRaises(ValidationError):
                self.create(evidence_ids=[evidence.pk])

    def test_each_policy_accepts_its_sources_and_gap_as_gap(self):
        for policy, ids in (("ACERVO_ONLY", [self.acervo.pk]), ("WEB_ONLY", [self.web.pk]), ("HYBRID", [self.acervo.pk, self.web.pk])):
            self.project.research_policy = policy
            self.project.save(update_fields=["research_policy"])
            expected = self.project.dossier_versions.count()
            dossier = self.create(expected_version=expected, evidence_ids=ids + [self.gap.pk], inherit_references=False,
                                  content={"research_gaps": [{"text": "Pesquisar mais", "reference_ids": [f"evidence:{self.gap.pk}"]}]})
            self.assertEqual(dossier.research_policy, policy)

    def test_policy_change_does_not_rewrite_history_or_silently_inherit_forbidden_sources(self):
        first = self.create(evidence_ids=[self.web.pk])
        self.project.research_policy = "ACERVO_ONLY"
        self.project.save(update_fields=["research_policy"])
        with self.assertRaises(ValidationError):
            self.create(expected_version=1)
        second = self.create(expected_version=1, inherit_references=False, evidence_ids=[self.acervo.pk])
        first.refresh_from_db()
        self.assertEqual((first.research_policy, second.research_policy), ("HYBRID", "ACERVO_ONLY"))

    def test_gap_and_untraceable_facts_are_rejected(self):
        for refs in ([], ["missing"], [f"evidence:{self.gap.pk}"]):
            with self.subTest(refs=refs), self.assertRaises(ValidationError):
                self.create(evidence_ids=[self.gap.pk], content={"facts": [{"text": "Alegação", "reference_ids": refs}]})

    def test_traceable_facts_are_accepted(self):
        dossier = self.create(evidence_ids=[self.web.pk], content={"facts": [{"text": "Afirmação documentada", "reference_ids": [f"evidence:{self.web.pk}"]}]})
        self.assertEqual(dossier.content["facts"][0]["reference_ids"], [f"evidence:{self.web.pk}"])

    def test_partial_draft_is_allowed_but_invalid_structure_is_not(self):
        for payload in ([], None, {"facts": "texto"}, {"facts": ["texto"]}, {"executive_summary": 1}, {"unknown": []}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                self.create(content=payload)
        self.assertEqual(self.create(content={}).content, {})

    def test_content_snapshot_and_lineage_are_immutable_on_save(self):
        dossier = self.create(evidence_ids=[self.web.pk])
        for field, value in (("content", {}), ("references_snapshot", []), ("version", 2), ("origin", "research_snapshot"), ("research_policy", "WEB_ONLY"), ("project_id", self.other_project.pk)):
            item = StudioDossierVersion.objects.get(pk=dossier.pk)
            setattr(item, field, value)
            with self.subTest(field=field), self.assertRaises(ValidationError):
                item.save()

    def test_orm_bulk_mutation_and_deletion_are_blocked(self):
        dossier = self.create()
        operations = (
            lambda: StudioDossierVersion.objects.filter(pk=dossier.pk).update(content={}),
            lambda: StudioDossierVersion.objects.bulk_update([dossier], ["content"]),
            lambda: StudioDossierVersion.objects.bulk_create([dossier]),
            lambda: StudioDossierVersion.objects.all().delete(),
            dossier.delete,
        )
        for operation in operations:
            with self.assertRaises(ValidationError):
                operation()
        self.assertEqual(self.project.dossier_versions.count(), 1)

    def test_approval_is_explicit_human_and_idempotent(self):
        dossier = self.create()
        with self.assertRaises(ValidationError):
            self.transition(dossier, "APPROVED")
        reviewed = self.transition(dossier, "REVIEW")
        self.assertIsNone(reviewed.reviewed_by_id)
        approved = self.transition(dossier, "APPROVED")
        self.assertEqual(approved.reviewed_by, self.owner)
        self.assertIsNotNone(approved.reviewed_at)
        repeated = self.transition(dossier, "APPROVED")
        self.assertEqual(repeated.reviewed_at, approved.reviewed_at)
        self.assertFalse(StudioApproval.objects.filter(project=self.project).exists())
        with self.assertRaises(ValidationError):
            self.transition(dossier, "DRAFT")

    def test_new_version_does_not_inherit_approval(self):
        first = self.create()
        self.transition(first, "REVIEW")
        self.transition(first, "APPROVED")
        second = self.create(expected_version=1)
        self.assertEqual(second.status, "DRAFT")
        self.assertIsNone(second.reviewed_by_id)
        self.assertIsNone(second.reviewed_at)
        first.refresh_from_db()
        self.assertEqual(first.status, "APPROVED")

    def test_foreign_and_stale_versions_cannot_be_approved(self):
        first = self.create()
        with self.assertRaises(PermissionDenied):
            self.transition(first, "REVIEW", actor=self.other)
        other = self.create(project_id=self.other_project.pk, actor=self.other)
        with self.assertRaises(ValidationError):
            self.transition(other, "REVIEW")
        self.create(expected_version=1)
        with self.assertRaises(ValidationError):
            self.transition(first, "REVIEW")

    def test_direct_creation_rejects_foreign_base_and_forged_snapshot(self):
        first = self.create(evidence_ids=[self.web.pk])
        values = dict(project=self.project, version=2, based_on=first, content={}, research_policy="HYBRID", created_by=self.owner)
        altered = deepcopy(first.references_snapshot)
        altered[0]["excerpt"] = "Texto inventado"
        with self.assertRaises(ValidationError):
            StudioDossierVersion.objects.create(**values, references_snapshot=altered)
        other = self.create(project_id=self.other_project.pk, actor=self.other)
        values["based_on"] = other
        with self.assertRaises(ValidationError):
            StudioDossierVersion.objects.create(**values)

    def test_database_rejects_duplicate_versions_and_approval_without_reviewer(self):
        dossier = self.create()
        # Base-manager writes deliberately exercise database constraints below ORM guards.
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudioDossierVersion._base_manager.filter(pk=dossier.pk).update(status="APPROVED")
        second = self.create(expected_version=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudioDossierVersion._base_manager.filter(pk=second.pk).update(version=1)


    def test_dossier_api_create_list_and_human_transition(self):
        client = APIClient()
        client.force_authenticate(user=self.owner)

        create_response = client.post(
            f"/api/library/studio/projects/{self.project.pk}/dossier/",
            {
                "content": {"executive_summary": "Versão criada pela API"},
                "expected_version": 0,
                "evidence_ids": [self.web.pk],
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        dossier_id = create_response.data["id"]
        self.assertEqual(create_response.data["status"], "DRAFT")
        self.assertEqual(create_response.data["version"], 1)

        list_response = client.get(
            f"/api/library/studio/projects/{self.project.pk}/dossier/"
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], dossier_id)

        review_response = client.post(
            f"/api/library/studio/projects/{self.project.pk}/dossier/{dossier_id}/transition/",
            {"expected_version": 1, "status": "REVIEW"},
            format="json",
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.data["status"], "REVIEW")

        approve_response = client.post(
            f"/api/library/studio/projects/{self.project.pk}/dossier/{dossier_id}/transition/",
            {"expected_version": 1, "status": "APPROVED"},
            format="json",
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.data["status"], "APPROVED")
        self.assertEqual(approve_response.data["reviewed_by"], self.owner.pk)
        self.assertIsNotNone(approve_response.data["reviewed_at"])

    def test_api_reference_inheritance_and_explicit_policy_replacement(self):
        client = APIClient()
        client.force_authenticate(user=self.owner)
        url = f"/api/library/studio/projects/{self.project.pk}/dossier/"
        first = self.create(evidence_ids=[self.acervo.pk, self.web.pk])
        inherited = client.post(url, {"content": {}, "expected_version": 1}, format="json")
        self.assertEqual(inherited.status_code, 201)
        self.assertEqual(inherited.data["references_snapshot"], first.references_snapshot)
        for version, policy, selected, kind in (
            (2, "ACERVO_ONLY", self.acervo.pk, "ACERVO"),
            (3, "WEB_ONLY", self.web.pk, "WEB"),
        ):
            self.project.research_policy = policy
            self.project.save(update_fields=["research_policy"])
            data = {"content": {}, "expected_version": version, "evidence_ids": [selected]}
            rejected = client.post(url, data, format="json")
            self.assertEqual(rejected.status_code, 400)
            response = client.post(url, {**data, "inherit_references": False}, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual([r["source_kind"] for r in response.data["references_snapshot"]], [kind])
        first.refresh_from_db()
        self.assertEqual({r["source_kind"] for r in first.references_snapshot}, {"ACERVO", "WEB"})

    def test_api_rejects_missing_and_foreign_evidence(self):
        client = APIClient()
        client.force_authenticate(user=self.owner)
        for evidence_id in (999999, self.foreign_evidence.pk):
            response = client.post(
                f"/api/library/studio/projects/{self.project.pk}/dossier/",
                {"content": {}, "expected_version": 0, "evidence_ids": [evidence_id], "inherit_references": False},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(self.project.dossier_versions.exists())

    def test_dossier_api_hides_foreign_project(self):
        client = APIClient()
        client.force_authenticate(user=self.owner)

        list_response = client.get(
            f"/api/library/studio/projects/{self.other_project.pk}/dossier/"
        )
        self.assertEqual(list_response.status_code, 404)

        create_response = client.post(
            f"/api/library/studio/projects/{self.other_project.pk}/dossier/",
            {"content": {}, "expected_version": 0},
            format="json",
        )
        self.assertEqual(create_response.status_code, 404)

    def test_dossier_api_rejects_stale_expected_version(self):
        dossier = self.create(evidence_ids=[self.web.pk])
        client = APIClient()
        client.force_authenticate(user=self.owner)

        response = client.post(
            f"/api/library/studio/projects/{self.project.pk}/dossier/",
            {
                "content": {"executive_summary": "Versão concorrente"},
                "expected_version": 0,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.project.dossier_versions.count(), 1)
        self.assertEqual(self.project.dossier_versions.first().pk, dossier.pk)

    def test_dossier_api_rejects_transition_of_old_version(self):
        first = self.create(evidence_ids=[self.web.pk])
        self.create(
            expected_version=1,
            content={"executive_summary": "Versão mais recente"},
        )
        client = APIClient()
        client.force_authenticate(user=self.owner)

        response = client.post(
            f"/api/library/studio/projects/{self.project.pk}/dossier/{first.pk}/transition/",
            {"expected_version": 1, "status": "REVIEW"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        first.refresh_from_db()
        self.assertEqual(first.status, "DRAFT")

    def test_research_prompt_context_prefers_approved_current_policy_dossier(self):
        dossier = self.create(
            evidence_ids=[self.web.pk],
            content={
                "facts": [{
                    "text": "Fato humano aprovado",
                    "reference_ids": [f"evidence:{self.web.pk}"],
                }]
            },
        )
        self.transition(dossier, "REVIEW")
        self.transition(dossier, "APPROVED")

        payload = research_prompt_context(self.project)

        self.assertIn('"dossier_version_id": %s' % dossier.pk, payload)
        self.assertIn('"Fato humano aprovado"', payload)
        self.assertNotIn('"Pesquisa automática"', payload)

    def test_research_prompt_context_ignores_approved_dossier_from_old_policy(self):
        dossier = self.create(
            evidence_ids=[self.web.pk],
            content={
                "facts": [{
                    "text": "Fato da política antiga",
                    "reference_ids": [f"evidence:{self.web.pk}"],
                }]
            },
        )
        self.transition(dossier, "REVIEW")
        self.transition(dossier, "APPROVED")

        self.project.research_policy = "ACERVO_ONLY"
        self.project.save(update_fields=["research_policy"])

        with self.assertRaises(StudioResearchError):
            research_prompt_context(self.project)

    def test_approved_without_references_is_editorial_guidance_only(self):
        dossier = self.create()
        self.transition(dossier, "REVIEW")
        self.transition(dossier, "APPROVED")
        payload = json.loads(research_prompt_context(self.project))
        self.assertEqual(payload["dossier"], dossier.content)
        self.assertEqual(payload["evidence"], [])
        self.assertFalse(payload["documentary_grounding"])
        self.assertIn("sem fundamentação documental", payload["context_role"])

    def test_new_draft_and_review_do_not_replace_approved_context(self):
        approved = self.create(evidence_ids=[self.web.pk])
        self.transition(approved, "REVIEW")
        self.transition(approved, "APPROVED")
        latest = self.create(expected_version=1, content={"executive_summary": "Ainda não aprovado"})
        for status in ("DRAFT", "REVIEW"):
            if status == "REVIEW":
                self.transition(latest, status)
            self.assertEqual(json.loads(research_prompt_context(self.project))["dossier_version_id"], approved.pk)

    def test_policy_changes_reject_incompatible_research_and_preserve_snapshot(self):
        approved = self.create(evidence_ids=[self.acervo.pk, self.web.pk])
        self.transition(approved, "REVIEW")
        self.transition(approved, "APPROVED")
        snapshot = deepcopy(approved.references_snapshot)
        for policy in ("ACERVO_ONLY", "WEB_ONLY"):
            self.project.research_policy = policy
            self.project.save(update_fields=["research_policy"])
            with self.assertRaises(StudioResearchError):
                research_prompt_context(self.project)
        approved.refresh_from_db()
        self.assertEqual(approved.references_snapshot, snapshot)

    @patch("library.views.buscar_chunks_relevantes", side_effect=AssertionError("No retrieval for snapshot"))
    @patch("library.views.generate_modernization_plan")
    def test_plan_reuses_historical_snapshots_and_records_version(self, generate, retrieve):
        from library.models import ModernizationPlan
        from library.tests.test_editorial_workflow import premium_plan
        client = APIClient()
        client.force_authenticate(user=self.owner)
        self.project.project_type = "formation"
        self.project.books.clear()
        for version, policy, ids in (
            (0, "ACERVO_ONLY", [self.acervo.pk]),
            (1, "WEB_ONLY", [self.web.pk]),
            (2, "HYBRID", [self.acervo.pk, self.web.pk]),
        ):
            self.project.research_policy = policy
            self.project.save(update_fields=["research_policy", "project_type"])
            approved = self.create(expected_version=version, evidence_ids=ids, inherit_references=False)
            self.transition(approved, "REVIEW")
            self.transition(approved, "APPROVED")
            generate.return_value = ({"proposed_architecture": premium_plan()}, "{}")
            response = client.post(f"/api/library/studio/projects/{self.project.pk}/generate-plan/", {}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            payload = json.loads(generate.call_args.args[3])
            self.assertEqual(payload["evidence"], approved.references_snapshot)
            self.assertTrue(payload["documentary_grounding"])
            provenance = ModernizationPlan.objects.get(project=self.project).proposed_architecture["dossier_provenance"]
            self.assertEqual(provenance["id"], approved.pk)
            self.assertEqual(provenance["version"], approved.version)
            self.assertEqual(provenance["research_policy"], policy)
            self.assertTrue(provenance["documentary_grounding"])
            self.assertEqual(self.project.plan_versions.first().content["dossier_provenance"], provenance)
            edited = premium_plan("Edição humana")
            edited["dossier_provenance"] = {"id": 999999}
            response = client.put(f"/api/library/studio/projects/{self.project.pk}/plan/", {"plan": edited}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(self.project.plan_versions.first().content["dossier_provenance"], provenance)
        retrieve.assert_not_called()

    @patch("library.services.studio_agents.chat_with_provider")
    def test_agent_uses_editorial_guidance_without_claiming_sources(self, chat):
        from library.services.studio_agents import generate_modernization_plan
        from library.tests.test_editorial_workflow import premium_plan
        approved = self.create()
        self.transition(approved, "REVIEW")
        self.transition(approved, "APPROVED")
        self.project.project_type = "formation"
        response = {"source_summary": "Sem fontes verificadas", "original_architecture": {},
                    "proposed_architecture": premium_plan(), "replacements": [], "requirements": {},
                    "acceptance_criteria": [], "test_strategy": {}, "risks": [], "business_value": "Valor"}
        chat.return_value = json.dumps(response)
        context = research_prompt_context(self.project)
        for chunks, mode in (([], "UNSOURCED_DRAFT"), ([self.chunk], "GROUNDED")):
            generate_modernization_plan(self.project, chunks, grounded_context=context)
            messages = chat.call_args.args[1]
            self.assertIn("Modo: " + mode, messages[1]["content"])
            self.assertIn("Síntese humana", messages[1]["content"])
            self.assertIn("NÃO invente" if not chunks else "Não invente", messages[0]["content"])
            if chunks:
                self.assertIn(self.chunk.content, messages[1]["content"])
            else:
                self.assertIn("NÃO É FONTE DOCUMENTAL", messages[1]["content"])
        self.assertEqual(json.loads(context)["evidence"], [])

    @patch("library.views.buscar_chunks_relevantes", side_effect=AssertionError("No retrieval"))
    @patch("library.views.generate_modernization_plan")
    def test_snapshot_survives_deleted_live_evidence(self, generate, retrieve):
        from library.tests.test_editorial_workflow import premium_plan
        approved = self.create(evidence_ids=[self.web.pk])
        self.transition(approved, "REVIEW")
        self.transition(approved, "APPROVED")
        self.context.delete()
        self.project.project_type = "formation"
        self.project.save(update_fields=["project_type"])
        generate.return_value = ({"proposed_architecture": premium_plan()}, "{}")
        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.post(f"/api/library/studio/projects/{self.project.pk}/generate-plan/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(json.loads(generate.call_args.args[3])["evidence"], approved.references_snapshot)
        self.assertFalse(self.project.citations.filter(purpose="modernization_plan").exists())

    @patch("library.views.buscar_chunks_relevantes", side_effect=AssertionError("No WEB_ONLY retrieval"))
    @patch("library.views.generate_modernization_plan")
    def test_web_only_fallback_drops_previous_hybrid_context(self, generate, retrieve):
        from library.tests.test_editorial_workflow import premium_plan
        self.project.research_policy = "WEB_ONLY"
        self.project.project_type = "formation"
        self.project.save(update_fields=["research_policy", "project_type"])
        generate.return_value = ({"proposed_architecture": premium_plan()}, "{}")
        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.post(f"/api/library/studio/projects/{self.project.pk}/generate-plan/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(generate.call_args.args[1], [])
        self.assertEqual(generate.call_args.args[3], "")

    def test_fallback_rejects_forbidden_evidence_even_when_policy_matches(self):
        self.project.research_policy = "WEB_ONLY"
        self.context.policy = "WEB_ONLY"
        self.context.save(update_fields=["policy"])
        with self.assertRaises(StudioResearchError):
            research_prompt_context(self.project)

    @patch("library.services.studio_research.validate_dossier", side_effect=ValidationError("Invalid snapshot"))
    def test_invalid_approved_snapshot_fails_closed(self, validate):
        approved = self.create(evidence_ids=[self.web.pk])
        self.transition(approved, "REVIEW")
        self.transition(approved, "APPROVED")
        with self.assertRaises(StudioResearchError):
            research_prompt_context(self.project)

    @patch("library.views.generate_modernization_plan")
    def test_acervo_without_documented_snapshot_still_requires_sources(self, generate):
        self.project.research_policy = "ACERVO_ONLY"
        self.project.save(update_fields=["research_policy"])
        self.project.books.clear()
        approved = self.create()
        self.transition(approved, "REVIEW")
        self.transition(approved, "APPROVED")
        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.post(f"/api/library/studio/projects/{self.project.pk}/generate-plan/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        generate.assert_not_called()

    def test_legacy_project_keeps_compatible_research(self):
        payload = json.loads(research_prompt_context(self.project))
        self.assertNotIn("dossier_version_id", payload)
        self.assertEqual(payload["dossier"], self.context.dossier)

    @patch("ai.services.chat_with_provider", side_effect=AssertionError("No AI"))
    def test_persistence_never_calls_ai_or_publishes(self, chat):
        from core.models import Course
        courses = Course.objects.count()
        project_state = self.project.status
        dossier = self.create()
        self.transition(dossier, "REVIEW")
        self.transition(dossier, "APPROVED")
        chat.assert_not_called()
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, project_state)
        self.assertEqual(Course.objects.count(), courses)
        self.assertFalse(self.project.artifacts.exists())
