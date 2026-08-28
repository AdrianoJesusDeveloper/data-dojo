from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import Book, ContentPackage, EditorialComment, EditorialPlanVersion, ModernizationPlan, StudioProject


def authorship():
    return {
        "independent_explanation": "Explique", "practical_challenge": "Construa",
        "portfolio_artifact": "Notebook", "reflection_question": "O que aprendeu?",
        "comprehension_criteria": "Defenda decisÃµes", "responsible_ai_use": "Registre o uso",
        "must_not_delegate_to_ai": "RaciocÃ­nio", "expected_result": "Entrega",
        "private_submission_option": "Envio privado",
    }


def premium_plan(title="Plano v1"):
    lesson = {
        "title": "Aula 1", "objective": "Aprender", "concepts": ["conceito"], "practice": "Praticar",
        "tools": ["Python"], "ai_integration": "Comparar alternativas", "human_reasoning": "Formular hipÃ³tese",
        "validation": "Testar", "reflection": "Explicar", "authorship_challenge": authorship(),
        "without_ai_challenge": "Refazer sem IA", "sources": ["Livro"], "expected_result": "Projeto",
    }
    module = {"title": "MÃ³dulo 1", "objective": "Base", "competencies": ["AnÃ¡lise"], "workload": "10h", "lessons": [lesson], "exercises": ["ExercÃ­cio"], "kata": "Kata", "practical_project": "Projeto", "assessment": "Rubrica"}
    return {
        "contract_version": "editorial-plan-v1", "title": title, "general_objective": "Formar",
        "professional_objective": "Atuar", "specific_objectives": ["Construir"], "target_audience": "Analistas",
        "level": "BÃ¡sico", "prerequisites": ["LÃ³gica"], "total_workload": "10h", "competencies": ["Dados"],
        "technology_stack": ["Python"], "module_count": 1, "lesson_count": 1, "methodology": "DojÃ´",
        "modules": [module], "practical_projects": ["Projeto"], "final_project": "Entrega final",
        "assessment_criteria": ["Qualidade"], "materials": ["Livro"], "completion_requirements": "Concluir",
        "certification_requirements": "Aprovar", "sources": ["Livro"], "ai_policy": "Humano raciocina, IA auxilia e o aluno valida.",
    }


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class EditorialWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(email="editor@example.com", username="editor", password="test", is_staff=True)
        self.other = get_user_model().objects.create_user(email="other-editor@example.com", username="other_editor", password="test", is_staff=True)
        self.client.force_authenticate(self.admin)
        self.project = StudioProject.objects.create(title="FormaÃ§Ã£o", theme="Dados", objective="Ensinar", project_type="premium", created_by=self.admin)

    def request(self, method, url, data=None):
        return getattr(self.client, method)(url, data=data, format="json" if data is not None else None, REMOTE_ADDR="127.0.0.1")

    def test_human_edit_validates_and_creates_immutable_history(self):
        current = ModernizationPlan.objects.create(project=self.project, proposed_architecture=premium_plan(), status="approved", version=1)
        edited = premium_plan("Plano v2")
        response = self.request("put", reverse("library-studio-plan-edit", kwargs={"pk": self.project.pk}), {"plan": edited})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        current.refresh_from_db()
        self.assertEqual(current.version, 2)
        self.assertEqual(current.status, "review")
        self.assertEqual(current.proposed_architecture["title"], "Plano v2")
        versions = EditorialPlanVersion.objects.filter(project=self.project).order_by("version")
        self.assertEqual(list(versions.values_list("version", flat=True)), [1, 2])
        self.assertEqual(versions[0].content["title"], "Plano v1")
        self.assertEqual(versions[1].origin, "human_edit")

        invalid = premium_plan("InvÃ¡lido")
        invalid["modules"] = []
        rejected = self.request("put", reverse("library-studio-plan-edit", kwargs={"pk": self.project.pk}), {"plan": invalid})
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        current.refresh_from_db()
        self.assertEqual(current.version, 2)

    def test_project_type_becomes_immutable_after_first_plan(self):
        before = self.request("patch", reverse("library-studio-project-detail", kwargs={"pk": self.project.pk}), {"project_type": "youtube"})
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.project_type, "youtube")
        ModernizationPlan.objects.create(project=self.project)
        after = self.request("patch", reverse("library-studio-project-detail", kwargs={"pk": self.project.pk}), {"project_type": "premium"})
        self.assertEqual(after.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comments_are_private_to_owner_and_can_be_resolved(self):
        plan = premium_plan()
        module_id = "module-stable-id"
        plan["modules"][0]["editorial_id"] = module_id
        ModernizationPlan.objects.create(project=self.project, proposed_architecture=plan, version=3)
        created = self.request("post", reverse("library-studio-comments", kwargs={"pk": self.project.pk}), {"text": "Rever objetivo", "target_type": "module", "target_id": module_id})
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        comment = EditorialComment.objects.get(pk=created.data["id"])
        self.assertEqual(comment.plan_version, 3)
        self.assertEqual(comment.target_id, module_id)
        resolved = self.request("post", reverse("library-studio-comment-resolve", kwargs={"pk": self.project.pk, "comment_pk": comment.pk}), {})
        self.assertEqual(resolved.status_code, status.HTTP_200_OK)
        self.assertTrue(resolved.data["resolved"])
        self.client.force_authenticate(self.other)
        denied = self.request("get", reverse("library-studio-comments", kwargs={"pk": self.project.pk}))
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)

    def test_archive_hides_restores_and_requires_confirmation_to_delete(self):
        archived = self.request("post", reverse("library-studio-archive", kwargs={"pk": self.project.pk}), {"archived": True})
        self.assertEqual(archived.status_code, status.HTTP_200_OK)
        active = self.request("get", reverse("library-studio-projects"))
        self.assertEqual(active.data["count"], 0)
        archive = self.client.get(reverse("library-studio-projects"), {"archived": "true"}, REMOTE_ADDR="127.0.0.1")
        self.assertEqual(archive.data["count"], 1)
        refused = self.request("delete", reverse("library-studio-permanent-delete", kwargs={"pk": self.project.pk}), {"confirmation": "nÃ£o"})
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        restored = self.request("post", reverse("library-studio-archive", kwargs={"pk": self.project.pk}), {"archived": False})
        self.assertEqual(restored.status_code, status.HTTP_200_OK)

    @patch("library.views.generate_content_item")
    def test_selective_content_requires_approval_and_stays_draft(self, generate):
        plan = ModernizationPlan.objects.create(project=self.project, proposed_architecture=premium_plan(), status="review")
        url = reverse("library-studio-generate-content", kwargs={"pk": self.project.pk})
        blocked = self.request("post", url, {"target_type": "lesson", "target_index": 0})
        self.assertEqual(blocked.status_code, status.HTTP_409_CONFLICT)
        plan.status = "approved"
        plan.save(update_fields=["status"])
        generate.return_value = ({"objective": "Aula produzida", "without_ai_challenge": "FaÃ§a sem IA"}, "raw")
        generated = self.request("post", url, {"target_type": "lesson", "target_index": 0})
        self.assertEqual(generated.status_code, status.HTTP_200_OK)
        package = ContentPackage.objects.get(project=self.project)
        self.assertEqual(package.publication_status, "draft")
        self.assertEqual(package.generated_items[0]["target_type"], "lesson")
        self.assertTrue(package.generated_items[0]["id"])
        self.assertEqual(package.generated_items[0]["plan_version"], plan.version)
        self.assertEqual(package.generated_items[0]["generation"], 1)
        self.assertEqual(package.generated_items[0]["status"], "draft")
        self.assertEqual(package.generated_items[0]["content"]["without_ai_challenge"], "FaÃ§a sem IA")

    @patch("library.views.buscar_chunks_relevantes", return_value=[object()])
    @patch("library.views.generate_modernization_plan")
    def test_stale_failed_generation_does_not_downgrade_newer_status(self, generate, buscar):
        book = Book.objects.create(title="Fonte", file="books/source.pdf", status="ready")
        self.project.books.add(book)

        def newer_execution_wins(*args, **kwargs):
            StudioProject.objects.filter(pk=self.project.pk).update(status="awaiting_approval")
            raise ValueError("falha antiga")

        generate.side_effect = newer_execution_wins
        response = self.request("post", reverse("library-studio-generate-plan", kwargs={"pk": self.project.pk}), {})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, "awaiting_approval")
