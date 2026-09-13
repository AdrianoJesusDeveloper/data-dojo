from copy import deepcopy
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from library.models import (
    Book, BookChunk, LibrarySource, SourceCitation, StudioApproval, StudioDossierVersion,
    StudioProject, StudioResearchContext, StudioResearchEvidence,
)
from library.services.studio_dossier import create_dossier_version, transition_dossier_version
from library.services.studio_research import build_research_context


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
