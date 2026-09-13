from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Course, Lesson, Module
from library.editorial_contracts import validate_editorial_plan
from library.models import Book, BookChunk, DidacticLesson, ModernizationPlan, SenseiFormation, StudioArtifact, StudioProject
from library.services.studio_formation import materialize_premium_formation
from library.services.studio_research import StudioResearchError, WebResearchProvider, WebResearchResult, build_research_context, generate_grounded_dossier
from library.tests.test_editorial_contracts import valid_plan


class FakeWebProvider(WebResearchProvider):
    def __init__(self, results=None):
        self.results = results if results is not None else [WebResearchResult(
            url="https://docs.python.org/3/tutorial/", title="Python Tutorial", excerpt="Documentação oficial da linguagem.",
            source_type="official_documentation", metadata={"authority": "primary"},
        )]

    def search(self, query, limit=5):
        return self.results


class ContentStudioMultiformatTests(APITestCase):
    def setUp(self):
        users = get_user_model().objects
        self.admin = users.create_user(email="multi@example.com", username="multi", password="test", is_staff=True)
        self.student = users.create_user(email="student-multi@example.com", username="student-multi", password="test")
        self.book = Book.objects.create(title="Livro interno", file="books/internal.pdf", status="ready")
        self.chunk = BookChunk.objects.create(book=self.book, chunk_index=0, page_number=7, content="Evidência interna verificável.")

    def project(self, policy, project_type="youtube"):
        project = StudioProject.objects.create(
            title="Projeto multiformato", theme="Programação e IA", objective="Produzir conteúdo fundamentado",
            original_intent="Vale a pena aprender programação em plena era da Inteligência Artificial?",
            project_type=project_type, research_policy=policy, created_by=self.admin,
        )
        if policy != "WEB_ONLY":
            project.books.add(self.book)
        return project

    @patch("library.services.studio_research.buscar_chunks_relevantes")
    def test_acervo_only_preserves_internal_provenance(self, retrieve):
        retrieve.return_value = [self.chunk]
        context = build_research_context(self.project("ACERVO_ONLY"), web_provider=Mock(side_effect=AssertionError))
        item = context.evidence.get()
        self.assertEqual((context.policy, context.status, item.source_kind, item.chunk_id), ("ACERVO_ONLY", "ready", "ACERVO", self.chunk.pk))
        self.assertEqual(item.url, "")

    def test_web_only_preserves_url_domain_query_and_retrieval_time(self):
        project = self.project("WEB_ONLY")
        context = build_research_context(project, FakeWebProvider())
        item = context.evidence.get()
        self.assertEqual(item.source_kind, "WEB")
        self.assertEqual(item.url, "https://docs.python.org/3/tutorial/")
        self.assertEqual(item.domain, "docs.python.org")
        self.assertEqual(item.query, project.original_intent)
        self.assertIsNotNone(item.retrieved_at)

    @patch("library.services.studio_research.buscar_chunks_relevantes")
    def test_hybrid_keeps_origins_separate(self, retrieve):
        retrieve.return_value = [self.chunk]
        context = build_research_context(self.project("HYBRID"), FakeWebProvider())
        self.assertEqual(set(context.evidence.values_list("source_kind", flat=True)), {"ACERVO", "WEB"})

    def test_empty_web_result_records_gap_without_inventing_reference(self):
        context = build_research_context(self.project("WEB_ONLY"), FakeWebProvider([]))
        item = context.evidence.get()
        self.assertEqual((context.status, item.source_kind, item.url, item.title), ("gap", "GAP", "", ""))

    @patch("library.services.studio_research.chat_with_provider")
    def test_dossier_rejects_invented_evidence_identifier(self, chat):
        chat.return_value = '{"dossier":{"evidence":[{"evidence_id":99}]},"conflicts":[]}'
        with self.assertRaises(StudioResearchError):
            generate_grounded_dossier(self.project("WEB_ONLY"), [{"source_kind": "WEB", "title": "Fonte", "url": "https://example.com", "excerpt": "Evidência"}])

    def test_intention_and_research_endpoint_are_admin_only(self):
        project = self.project("WEB_ONLY")
        self.client.force_authenticate(self.student)
        response = self.client.post(reverse("library-studio-research", kwargs={"pk": project.pk}), {}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_youtube_artifact_has_independent_workflow_exports_and_never_publishes(self):
        project = self.project("WEB_ONLY")
        artifact = StudioArtifact.objects.create(project=project, artifact_type="YOUTUBE_PACKAGE", target_type="video", target_id="video-1", plan_version=1, content={"title": "Programação na era da IA", "script": "Abertura e roteiro completo", "teleprompter_text": "Abertura e roteiro completo"}, created_by=self.admin)
        self.client.force_authenticate(self.admin)
        url = reverse("library-studio-artifact-transition", kwargs={"pk": artifact.pk})
        review = self.client.post(url, {"status": "REVIEW"}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        approved = self.client.post(url, {"status": "APPROVED"}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(approved.data["status"], "APPROVED")
        for export_format in ("docx", "html", "teleprompter"):
            exported = self.client.get(reverse("library-studio-artifact-export", kwargs={"pk": artifact.pk, "export_format": export_format}), REMOTE_ADDR="127.0.0.1")
            self.assertEqual(exported.status_code, status.HTTP_200_OK)
        self.assertEqual((Course.objects.count(), Module.objects.count(), Lesson.objects.count()), (0, 0, 0))

    def test_premium_materialization_is_idempotent_and_does_not_generate_lessons_or_progress(self):
        initial_formations = SenseiFormation.objects.count()
        project = self.project("ACERVO_ONLY", "premium")
        plan = validate_editorial_plan("premium", valid_plan("premium"))
        model = ModernizationPlan.objects.create(project=project, proposed_architecture=plan, status="approved", version=1)
        first, changed = materialize_premium_formation(project, self.admin)
        first_ids = (first.formation_id, first.formation.modules.get().pk, first.formation.modules.get().study_units.get().pk)
        second, changed_again = materialize_premium_formation(project, self.admin)
        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual((second.formation_id, second.formation.modules.get().pk, second.formation.modules.get().study_units.get().pk), first_ids)
        plan["title"] = "Formação atualizada"
        model.proposed_architecture, model.version = plan, 2
        model.save(update_fields=["proposed_architecture", "version"])
        third, changed_update = materialize_premium_formation(project, self.admin)
        self.assertTrue(changed_update)
        self.assertEqual(third.formation_id, first_ids[0])
        self.assertEqual((SenseiFormation.objects.count(), DidacticLesson.objects.count(), Course.objects.count()), (initial_formations + 1, 0, 0))
