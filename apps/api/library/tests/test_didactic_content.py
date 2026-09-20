import json
import os
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from docx import Document

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import (
    Book, DidacticLesson, DidacticLessonSection, LibrarySource, SenseiCompetency, SenseiCompetencyEvidence,
    SenseiCompetencyProgress, SenseiFormation, SenseiFormationModule, SenseiStudyUnit,
    SenseiUnitSource, SenseiUnitStudyPlan,
)


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class DidacticContentApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="didactic@example.com", username="didactic", password="test", is_staff=True)
        self.client.force_authenticate(self.user)
        self.formation = SenseiFormation.objects.create(title="Formação didática", slug="didactic-formation", description="", objective="Ensinar", status="DRAFT", level="Progressivo", created_by=self.user)
        self.module = SenseiFormationModule.objects.create(formation=self.formation, title="Fundamentos", order=0)
        self.unit = SenseiStudyUnit.objects.create(module=self.module, title="Unidade didática", objective="Explicar", order=0, status="ACTIVE")
        self.competency = SenseiCompetency.objects.create(formation=self.formation, module=self.module, title="Explicar fundamentos", expected_level=4, mastery_criteria=["Explica"])
        self.plan = SenseiUnitStudyPlan.objects.create(unit=self.unit, learning_objectives=["Explicar"], practices=["Praticar"], expected_evidence=["Artefato"], completion_criteria=["Justificar"])
        self.plan.related_competencies.add(self.competency)
        self.url = reverse("library-sensei-unit-didactic-content", kwargs={"pk": self.unit.pk})

    def request(self, method, data=None):
        return getattr(self.client, method)(self.url, data=data, format="json" if data is not None else None, REMOTE_ADDR="127.0.0.1")

    def approved_source(self, title="Fonte aprovada"):
        return SenseiUnitSource.objects.create(unit=self.unit, category="FOUNDATIONAL", source_type="TECHNICAL_BOOK", title=title, reference="Capítulo 1", location="Seção 1", objective="Fundamentar", priority=1, justification="Fonte revisada.", editorial_status="APPROVED")

    def ai_response(self):
        return json.dumps({"sections": [
            {"section_type": "CONCEPT", "title": "Conceito", "content": "Explicação estruturada.", "metadata": {"depth": "core"}},
            {"section_type": "AUTHORSHIP_CHALLENGE", "title": "Desafio de autoria", "content": "Explique, aplique, reflita e entregue um artefato.", "metadata": {"requires_artifact": True}},
        ]})

    @patch("library.services.didactic_content.buscar_chunks_relevantes")
    def test_approved_library_source_adds_retrieved_excerpts_to_context(self, retrieve):
        source = LibrarySource.objects.create(
            relative_path="didactic/python.pdf",
            filename="python.pdf",
            extension="pdf",
            status="supported",
        )
        book = Book.objects.create(
            title="Python prático",
            source=source,
            file="library/books/python.pdf",
            status="ready",
        )
        SenseiUnitSource.objects.create(
            unit=self.unit,
            source=source,
            category="FOUNDATIONAL",
            source_type="TECHNICAL_BOOK",
            title="Python prático",
            reference="Edição local",
            location="Capítulo 2, PDF p.30 a 45",
            approved_ranges=[{"pdf_start": 30, "pdf_end": 45}],
            objective="Fundamentar estruturas de dados",
            priority=1,
            justification="Fonte revisada e diretamente relacionada.",
            editorial_status="APPROVED",
        )
        retrieve.return_value = [
            SimpleNamespace(id=99, book_id=book.id, book=book, page_number=33, chunk_index=7, content="Listas são coleções mutáveis em Python."),
        ]

        from library.services.didactic_content import build_didactic_context

        context, sources, source_mode = build_didactic_context(self.unit)

        self.assertEqual(source_mode, DidacticLesson.SourceMode.APPROVED_SOURCES)
        self.assertEqual(len(sources), 1)
        self.assertEqual(context["approved_source_excerpts"][0]["book_title"], "Python prático")
        self.assertEqual(context["approved_source_excerpts"][0]["pdf_page"], 33)
        self.assertEqual(context["approved_source_excerpts"][0]["chunk_id"], 99)
        self.assertEqual(context["approved_source_excerpts"][0]["approved_ranges"], [{"pdf_start": 30, "pdf_end": 45}])
        self.assertIn("coleções mutáveis", context["approved_source_excerpts"][0]["content"])
        retrieve.assert_called_once()
        _, kwargs = retrieve.call_args
        self.assertEqual(kwargs["allowed_ranges_by_book"], {book.id: [{"pdf_start": 30, "pdf_end": 45}]})

    @patch.dict(os.environ, {"SENSEI_AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key", "GROQ_MODEL": "didactic-model"}, clear=False)
    @patch("library.services.didactic_content.buscar_chunks_relevantes")
    @patch("library.services.didactic_content.chat_with_provider")
    def test_generation_persists_exact_grounding_snapshot(self, provider, retrieve):
        source = LibrarySource.objects.create(
            relative_path="didactic/grounded.pdf",
            filename="grounded.pdf",
            extension="pdf",
            status="supported",
        )
        book = Book.objects.create(
            title="Grounded Python",
            source=source,
            file="library/books/grounded.pdf",
            status="ready",
        )
        approved = SenseiUnitSource.objects.create(
            unit=self.unit,
            source=source,
            category="FOUNDATIONAL",
            source_type="TECHNICAL_BOOK",
            title="Grounded Python",
            reference="Edição local",
            location="Capítulo 6, PDF p.122 a 135",
            approved_ranges=[{"pdf_start": 122, "pdf_end": 135}],
            objective="Fundamentar",
            priority=1,
            justification="Fonte revisada.",
            editorial_status="APPROVED",
        )
        retrieve.return_value = [
            SimpleNamespace(
                id=321,
                book_id=book.id,
                book=book,
                page_number=124,
                chunk_index=123,
                content="As listas são mutáveis e aceitam alterações no local.",
            ),
        ]
        provider.return_value = self.ai_response()

        response = self.request("post", {})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        lesson = DidacticLesson.objects.get(pk=response.data["id"])
        self.assertEqual(lesson.grounding_snapshot["provider"], "groq")
        self.assertEqual(lesson.grounding_snapshot["model"], "didactic-model")
        self.assertEqual(lesson.grounding_snapshot["sources"][0]["id"], approved.id)
        excerpt = lesson.grounding_snapshot["excerpts"][0]
        self.assertEqual((excerpt["book_id"], excerpt["pdf_page"], excerpt["chunk_id"]), (book.id, 124, 321))
        self.assertEqual(excerpt["approved_ranges"], [{"pdf_start": 122, "pdf_end": 135}])

    @patch.dict(os.environ, {"SENSEI_AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key", "GROQ_MODEL": "didactic-model"}, clear=False)
    @patch("library.services.didactic_content.chat_with_provider")
    def test_generates_draft_with_ordered_sections_approved_sources_and_provenance(self, provider):
        source = self.approved_source()
        provider.return_value = self.ai_response()
        response = self.request("post", {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        lesson = DidacticLesson.objects.get(pk=response.data["id"])
        self.assertEqual((lesson.status, lesson.audience, lesson.ai_provider, lesson.ai_model), ("DRAFT", "SENSEI", "groq", "didactic-model"))
        self.assertEqual(list(lesson.sections.values_list("section_type", "order")), [("CONCEPT", 0), ("AUTHORSHIP_CHALLENGE", 1)])
        self.assertEqual(list(lesson.sources.values_list("id", flat=True)), [source.id])
        self.assertEqual(self.request("get").data["lesson"]["sections"][0]["title"], "Conceito")

    @patch.dict(os.environ, {"SENSEI_AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"}, clear=False)
    @patch("library.services.didactic_content.chat_with_provider")
    def test_generation_is_idempotent_and_blocks_without_approved_source(self, provider):
        blocked = self.request("post", {})
        self.assertEqual(blocked.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("NEEDS_SOURCE", blocked.data["detail"])
        self.approved_source()
        provider.return_value = self.ai_response()
        first = self.request("post", {})
        second = self.request("post", {})
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(provider.call_count, 1)

    @patch.dict(os.environ, {"SENSEI_AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key"}, clear=False)
    @patch("library.services.didactic_content.chat_with_provider")
    def test_human_update_status_and_provenance_are_safe(self, provider):
        source = self.approved_source()
        provider.return_value = self.ai_response()
        lesson = self.request("post", {}).data
        updated = self.client.patch(self.url, {"status": "REVIEW", "sections": [{"section_type": "CONCEPT", "title": "Edição humana", "content": "Conteúdo revisado.", "order": 0, "metadata": {}}]}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
        stored = DidacticLesson.objects.get(pk=lesson["id"])
        self.assertEqual(stored.status, "REVIEW")
        self.assertEqual(stored.sections.get().title, "Edição humana")
        self.assertEqual(stored.ai_provider, "groq")
        self.assertEqual(updated.data["source_provenance"][0]["id"], source.id)
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency=self.competency).exists())
        self.assertFalse(SenseiCompetencyProgress.objects.filter(competency=self.competency).exists())

    def test_editorial_workflow_draft_review_approved_is_separate_from_learning(self):
        content_type = ContentType.objects.get_for_model(self.unit)
        lesson = DidacticLesson.objects.create(title="Editorial", audience="SENSEI", status="DRAFT", learning_target_type=content_type, learning_target_id=self.unit.id, author=self.user)
        initial_xp = self.user.xp_points
        review = self.client.patch(self.url, {"status": "REVIEW"}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual((review.status_code, review.data["status"]), (status.HTTP_200_OK, "REVIEW"))
        approved = self.client.patch(self.url, {"status": "APPROVED"}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual((approved.status_code, approved.data["status"]), (status.HTTP_200_OK, "APPROVED"))
        lesson.refresh_from_db(); self.user.refresh_from_db()
        self.assertEqual(lesson.reviewed_by, self.user)
        self.assertEqual(self.user.xp_points, initial_xp)
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency=self.competency).exists())
        self.assertFalse(SenseiCompetencyProgress.objects.filter(competency=self.competency).exists())

    def test_non_staff_cannot_change_didactic_lesson_status(self):
        content_type = ContentType.objects.get_for_model(self.unit)
        lesson = DidacticLesson.objects.create(title="Editorial", audience="SENSEI", status="DRAFT", learning_target_type=content_type, learning_target_id=self.unit.id, author=self.user)
        student = get_user_model().objects.create_user(email="no-editor@example.com", username="no-editor", password="test")
        self.client.force_authenticate(student)
        response = self.client.patch(self.url, {"status": "REVIEW"}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, "DRAFT")

    def test_human_lesson_without_ai_provenance_does_not_invent_metadata(self):
        content_type = ContentType.objects.get_for_model(self.unit)
        lesson = DidacticLesson.objects.create(title="Humana", audience="SENSEI", status="DRAFT", learning_target_type=content_type, learning_target_id=self.unit.id, author=self.user)
        DidacticLessonSection.objects.create(lesson=lesson, section_type="CONCEPT", title="Conceito", content="Escrito por pessoa.", order=0)
        payload = self.request("get").data["lesson"]
        self.assertEqual((payload["ai_provider"], payload["ai_model"]), ("", ""))

    def test_exports_complete_ordered_lesson_as_docx_and_html(self):
        content_type = ContentType.objects.get_for_model(self.unit)
        lesson = DidacticLesson.objects.create(
            title="Aula Exportável", audience="SENSEI", status="DRAFT",
            source_mode="AI_GENERATED_UNSOURCED", learning_target_type=content_type,
            learning_target_id=self.unit.id, author=self.user, ai_provider="groq", ai_model="model-1",
        )
        DidacticLessonSection.objects.create(lesson=lesson, section_type="EXERCISE", title="Segundo", content="Pratique.", order=1)
        DidacticLessonSection.objects.create(lesson=lesson, section_type="CONCEPT", title="Primeiro", content="Compreenda.", order=0)
        source = self.approved_source()
        lesson.sources.add(source)

        base = reverse("library-sensei-unit-didactic-content-export", kwargs={"pk": self.unit.pk, "export_format": "docx"})
        docx_response = self.client.get(base, REMOTE_ADDR="127.0.0.1")
        self.assertEqual(docx_response.status_code, status.HTTP_200_OK)
        self.assertEqual(docx_response["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", docx_response["Content-Disposition"])
        document = Document(BytesIO(docx_response.content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertLess(text.index("Primeiro"), text.index("Segundo"))
        for expected in ("Formação didática", "Fundamentos", "Unidade didática", "groq / model-1", "sem fonte aprovada", "aula #"):
            self.assertIn(expected, text)

        html_url = reverse("library-sensei-unit-didactic-content-export", kwargs={"pk": self.unit.pk, "export_format": "html"})
        html_response = self.client.get(html_url, REMOTE_ADDR="127.0.0.1")
        html = html_response.content.decode("utf-8")
        self.assertEqual(html_response.status_code, status.HTTP_200_OK)
        self.assertLess(html.index("Primeiro"), html.index("Segundo"))
        self.assertIn("AI_GENERATED_UNSOURCED", html)
        self.assertIn("Fonte aprovada", html)
        self.assertNotIn("Iniciar Desafio", html)

    def test_export_requires_visible_existing_lesson_and_supported_format(self):
        for export_format in ("docx", "html"):
            url = reverse("library-sensei-unit-didactic-content-export", kwargs={"pk": self.unit.pk, "export_format": export_format})
            self.assertEqual(self.client.get(url, REMOTE_ADDR="127.0.0.1").status_code, status.HTTP_404_NOT_FOUND)

        content_type = ContentType.objects.get_for_model(self.unit)
        DidacticLesson.objects.create(title="Aula", audience="SENSEI", learning_target_type=content_type, learning_target_id=self.unit.id, author=self.user)
        unsupported = reverse("library-sensei-unit-didactic-content-export", kwargs={"pk": self.unit.pk, "export_format": "pdf"})
        self.assertEqual(self.client.get(unsupported, REMOTE_ADDR="127.0.0.1").status_code, status.HTTP_404_NOT_FOUND)

    def test_lesson_is_isolated_by_unit_and_permission(self):
        other_user = get_user_model().objects.create_user(email="other-didactic@example.com", username="other-didactic", password="test", is_staff=True)
        self.client.force_authenticate(other_user)
        self.assertEqual(self.request("get").status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.user)
        other_module = SenseiFormationModule.objects.create(formation=self.formation, title="Outro", order=1)
        other_unit = SenseiStudyUnit.objects.create(module=other_module, title="Outra", objective="Outra", order=0, status="ACTIVE")
        self.assertEqual(self.client.get(reverse("library-sensei-unit-didactic-content", kwargs={"pk": other_unit.pk}), format="json").data["lesson"], None)

    def _seed_named_unit(self, slug, source_policy):
        formation, _ = SenseiFormation.objects.get_or_create(slug=slug, defaults={"title": slug, "description": "", "objective": "Ensinar", "status": "DRAFT", "level": "Progressivo", "source_policy": source_policy})
        formation.source_policy = source_policy
        formation.save(update_fields=["source_policy"])
        module, _ = SenseiFormationModule.objects.get_or_create(formation=formation, order=0, defaults={"title": "Módulo", "description": ""})
        unit, _ = SenseiStudyUnit.objects.get_or_create(module=module, order=0, defaults={"title": slug, "objective": "Explicar", "status": "ACTIVE"})
        competency, _ = SenseiCompetency.objects.get_or_create(formation=formation, module=module, order=0, defaults={"title": "Competência", "expected_level": 4, "mastery_criteria": ["Explica"]})
        plan, _ = SenseiUnitStudyPlan.objects.get_or_create(unit=unit, defaults={"learning_objectives": ["Explicar"], "practices": ["Praticar"], "expected_evidence": ["Artefato"], "completion_criteria": ["Justificar"]})
        plan.related_competencies.add(competency)
        return formation, unit

    @patch.dict(os.environ, {"SENSEI_AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key", "GROQ_MODEL": "test-model"}, clear=False)
    @patch("library.services.didactic_content.chat_with_provider")
    def test_001_with_approved_source_records_approved_sources(self, provider):
        formation, unit = self._seed_named_unit("engenharia-ia-arquitetura-sistemas-inteligentes", "REQUIRE_APPROVED_SOURCE")
        source = SenseiUnitSource.objects.create(unit=unit, category="FOUNDATIONAL", source_type="TECHNICAL_BOOK", title="Fonte 001", reference="Capítulo 1", objective="Fundamentar", priority=1, justification="Revisada", editorial_status="APPROVED")
        provider.return_value = self.ai_response()
        response = self.client.post(reverse("library-sensei-unit-didactic-content", kwargs={"pk": unit.pk}), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        lesson = DidacticLesson.objects.get(pk=response.data["id"])
        self.assertEqual(lesson.source_mode, DidacticLesson.SourceMode.APPROVED_SOURCES)
        self.assertEqual(list(lesson.sources.values_list("id", flat=True)), [source.id])
        self.assertEqual(lesson.status, DidacticLesson.Status.DRAFT)

    def test_001_without_approved_source_blocks_safely(self):
        _, unit = self._seed_named_unit("engenharia-ia-arquitetura-sistemas-inteligentes", "REQUIRE_APPROVED_SOURCE")
        response = self.client.post(reverse("library-sensei-unit-didactic-content", kwargs={"pk": unit.pk}), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("NEEDS_SOURCE", response.data["detail"])
        self.assertFalse(DidacticLesson.objects.filter(learning_target_id=unit.pk).exists())

    @patch.dict(os.environ, {"SENSEI_AI_PROVIDER": "groq", "GROQ_API_KEY": "test-key", "GROQ_MODEL": "test-model"}, clear=False)
    @patch("library.services.didactic_content.chat_with_provider")
    def test_002_without_source_records_unsourced_draft_without_auto_approval(self, provider):
        _, unit = self._seed_named_unit("marketing-digital-performance-gestao-de-trafego-pago", "ALLOW_AI_WITHOUT_SOURCE")
        provider.return_value = self.ai_response()
        response = self.client.post(reverse("library-sensei-unit-didactic-content", kwargs={"pk": unit.pk}), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        lesson = DidacticLesson.objects.get(pk=response.data["id"])
        self.assertEqual(lesson.source_mode, DidacticLesson.SourceMode.AI_GENERATED_UNSOURCED)
        self.assertEqual(lesson.status, DidacticLesson.Status.DRAFT)
        self.assertIsNone(lesson.reviewed_by)
        self.assertIsNone(lesson.published_at)
