from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Course, CourseProgress, Lesson, LessonProgress, Module
from library.models import DidacticLesson, DidacticLessonSection, DidacticPublication, SenseiCompetencyEvidence, SenseiCompetencyProgress, SenseiFormation, SenseiFormationModule, SenseiProgress, SenseiStudyUnit, SenseiUnitStudyPlan


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class DidacticPublicationTests(APITestCase):
    def setUp(self):
        users = get_user_model().objects
        self.user = users.create_user(email="publisher@example.com", username="publisher", password="test", is_staff=True)
        self.other = users.create_user(email="other-publisher@example.com", username="other-publisher", password="test", is_staff=True)
        self.student = users.create_user(email="student-publisher@example.com", username="student-publisher", password="test")
        self.formation = SenseiFormation.objects.create(title="Formação", slug="publish-formation", objective="Ensinar", status="ACTIVE", created_by=self.user)
        self.module = SenseiFormationModule.objects.create(formation=self.formation, title="Módulo A", order=0)
        self.unit = SenseiStudyUnit.objects.create(module=self.module, title="Unidade A", objective="Aplicar", order=0, status="ACTIVE")
        SenseiUnitStudyPlan.objects.create(unit=self.unit, learning_objectives=["Explicar"], completion_criteria=["Justificar a decisão"])
        self.lesson = self.make_lesson(self.unit, "Aula A")
        self.preview_url = reverse("library-sensei-publication-preview", kwargs={"pk": self.unit.pk})
        self.publish_url = reverse("library-sensei-publication-publish", kwargs={"pk": self.unit.pk})
        self.client.force_authenticate(self.user)

    def make_lesson(self, unit, title, status_value="APPROVED"):
        lesson = DidacticLesson.objects.create(
            title=title, audience="SENSEI", status=status_value, source_mode="AI_GENERATED_UNSOURCED",
            learning_target_type=ContentType.objects.get_for_model(unit), learning_target_id=unit.pk,
            author=self.user, ai_provider="groq", ai_model="model-1",
        )
        DidacticLessonSection.objects.create(lesson=lesson, section_type="CONCEPT", title="Conceito", content="Conteúdo Sensei", order=0)
        DidacticLessonSection.objects.create(lesson=lesson, section_type="AUTHORSHIP_CHALLENGE", title="Autoria", content="Explique a decisão", order=1)
        return lesson

    def post(self, url, data):
        return self.client.post(url, data, format="json", REMOTE_ADDR="127.0.0.1")

    def preview(self, scope="LESSON"):
        return self.post(self.preview_url, {"scope": scope})

    def test_preview_adapts_explicitly_without_writing_workspace(self):
        response = self.preview()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual((Course.objects.count(), Module.objects.count(), Lesson.objects.count()), (0, 0, 0))
        item = response.data["items"][0]
        self.assertEqual(item["audience"], "STUDENT")
        self.assertTrue(item["adaptation"]["human_publication_required"])
        self.assertTrue(item["adaptation"]["does_not_grant_mastery"])
        self.assertIn("próprias palavras", item["sections"][0]["content"])
        self.assertEqual(item["sections"][-1]["section_type"], "MASTERY_CRITERIA")
        self.assertEqual(DidacticPublication.objects.get().status, "PREVIEW")
        self.assertFalse(DidacticLesson.objects.filter(audience="STUDENT").exists())

    def test_publish_creates_traceable_student_and_existing_workspace_models(self):
        academic_counts = (
            CourseProgress.objects.count(), LessonProgress.objects.count(), SenseiProgress.objects.count(),
            SenseiCompetencyEvidence.objects.count(), SenseiCompetencyProgress.objects.count(),
        )
        preview = self.preview().data
        response = self.post(self.publish_url, {"preview_token": preview["preview_token"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        student = DidacticLesson.objects.get(audience="STUDENT")
        self.lesson.refresh_from_db()
        self.formation.refresh_from_db()
        self.assertEqual(student.origin_lesson, self.lesson)
        self.assertEqual(student.origin_updated_at, self.lesson.updated_at)
        self.assertEqual(student.status, "PUBLISHED")
        self.assertEqual(student.workspace_lesson.body.splitlines()[0], "## Conceito")
        self.assertEqual(student.workspace_lesson.module.course, self.formation.workspace_course)
        self.assertEqual(response.data["items"][0]["stale"], False)
        self.assertEqual(DidacticPublication.objects.get().status, "PUBLISHED")
        self.assertEqual((
            CourseProgress.objects.count(), LessonProgress.objects.count(), SenseiProgress.objects.count(),
            SenseiCompetencyEvidence.objects.count(), SenseiCompetencyProgress.objects.count(),
        ), academic_counts)

    def test_module_and_formation_scopes_select_exact_lessons(self):
        unit_b = SenseiStudyUnit.objects.create(module=self.module, title="Unidade B", objective="B", order=1, status="ACTIVE")
        self.make_lesson(unit_b, "Aula B")
        module_b = SenseiFormationModule.objects.create(formation=self.formation, title="Módulo B", order=1)
        unit_c = SenseiStudyUnit.objects.create(module=module_b, title="Unidade C", objective="C", order=0, status="ACTIVE")
        self.make_lesson(unit_c, "Aula C")
        self.assertEqual(len(self.preview("LESSON").data["items"]), 1)
        self.assertEqual(len(self.preview("MODULE").data["items"]), 2)
        formation_preview = self.preview("FORMATION")
        self.assertEqual(len(formation_preview.data["items"]), 3)
        published = self.post(self.publish_url, {"preview_token": formation_preview.data["preview_token"]})
        self.assertEqual(published.status_code, status.HTTP_200_OK, published.data)
        self.formation.refresh_from_db()
        self.assertEqual((self.formation.workspace_course.modules.count(), Lesson.objects.count()), (2, 3))

    def test_module_preview_classifies_every_unit_and_publishes_only_approved(self):
        draft_unit = SenseiStudyUnit.objects.create(module=self.module, title="Rascunho", objective="B", order=1, status="ACTIVE")
        review_unit = SenseiStudyUnit.objects.create(module=self.module, title="Revisão", objective="C", order=2, status="ACTIVE")
        empty_unit = SenseiStudyUnit.objects.create(module=self.module, title="Sem aula", objective="D", order=3, status="ACTIVE")
        self.make_lesson(draft_unit, "Aula rascunho", "DRAFT")
        self.make_lesson(review_unit, "Aula revisão", "REVIEW")

        response = self.preview("MODULE")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["summary"], {"total": 4, "eligible": 1, "ineligible": 3})
        reasons = {item["unit_title"]: item["eligibility"] for item in response.data["eligibility_items"]}
        self.assertEqual(reasons, {
            "Unidade A": "ELIGIBLE", "Rascunho": "INELIGIBLE_DRAFT",
            "Revisão": "INELIGIBLE_REVIEW", "Sem aula": "INELIGIBLE_NO_DIDACTIC_LESSON",
        })
        published = self.post(self.publish_url, {"preview_token": response.data["preview_token"]})
        self.assertEqual(published.status_code, status.HTTP_200_OK, published.data)
        self.assertEqual([item["source_lesson_id"] for item in published.data["items"]], [self.lesson.pk])
        self.assertEqual(Lesson.objects.count(), 1)
        self.assertFalse(DidacticLesson.objects.filter(learning_target_id__in=[draft_unit.pk, review_unit.pk, empty_unit.pk], audience="STUDENT").exists())

    def test_zero_eligible_preview_blocks_without_empty_workspace_hierarchy(self):
        self.lesson.status = "ARCHIVED"
        self.lesson.save(update_fields=["status", "updated_at"])
        preview = self.preview("MODULE")
        self.assertEqual(preview.data["summary"], {"total": 1, "eligible": 0, "ineligible": 1})
        self.assertEqual(preview.data["eligibility_items"][0]["eligibility"], "INELIGIBLE_ARCHIVED")
        denied = self.post(self.publish_url, {"preview_token": preview.data["preview_token"]})
        self.assertEqual(denied.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual((Course.objects.count(), Module.objects.count(), Lesson.objects.count()), (0, 0, 0))

    def test_republishing_lesson_in_module_reuses_all_derivations(self):
        lesson_preview = self.preview("LESSON").data
        self.assertEqual(self.post(self.publish_url, {"preview_token": lesson_preview["preview_token"]}).status_code, status.HTTP_200_OK)
        self.formation.refresh_from_db()
        self.module.refresh_from_db()
        first_ids = (
            self.formation.workspace_course_id,
            self.module.workspace_module_id,
            DidacticLesson.objects.get(origin_lesson=self.lesson).workspace_lesson_id,
        )
        module_preview = self.preview("MODULE").data
        self.assertEqual(self.post(self.publish_url, {"preview_token": module_preview["preview_token"]}).status_code, status.HTTP_200_OK)
        self.formation.refresh_from_db()
        self.module.refresh_from_db()
        student = DidacticLesson.objects.get(origin_lesson=self.lesson)
        self.assertEqual((self.formation.workspace_course_id, self.module.workspace_module_id, student.workspace_lesson_id), first_ids)
        self.assertEqual((Course.objects.count(), Module.objects.count(), Lesson.objects.count()), (1, 1, 1))

    def test_formation_preview_groups_multiple_modules_and_invalidates_on_scope_change(self):
        module_b = SenseiFormationModule.objects.create(formation=self.formation, title="Módulo B", order=1)
        unit_b = SenseiStudyUnit.objects.create(module=module_b, title="Unidade B", objective="B", order=0, status="ACTIVE")
        self.make_lesson(unit_b, "Aula B")
        empty = SenseiStudyUnit.objects.create(module=module_b, title="Sem aula B", objective="C", order=1, status="ACTIVE")
        preview = self.preview("FORMATION")
        self.assertEqual(preview.data["summary"], {"total": 3, "eligible": 2, "ineligible": 1})
        self.assertEqual({item["module_title"] for item in preview.data["eligibility_items"]}, {"Módulo A", "Módulo B"})
        empty.title = "Origem alterada"
        empty.save(update_fields=["title"])
        denied = self.post(self.publish_url, {"preview_token": preview.data["preview_token"]})
        self.assertEqual(denied.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("mudou", denied.data["detail"])

    def test_new_preview_detects_student_derivation_as_stale(self):
        first = self.preview().data
        self.assertEqual(self.post(self.publish_url, {"preview_token": first["preview_token"]}).status_code, status.HTTP_200_OK)
        self.lesson.title = "Aula revisada"
        self.lesson.save(update_fields=["title", "updated_at"])
        next_preview = self.preview().data["items"][0]
        self.assertTrue(next_preview["student_is_stale"])
        self.assertIsNotNone(next_preview["existing_student_lesson_id"])
        eligibility = self.preview().data["eligibility_items"][0]
        self.assertTrue(eligibility["student_is_stale"])

    def test_publish_rejects_draft_changed_reused_or_foreign_preview(self):
        self.lesson.status = "DRAFT"
        self.lesson.save(update_fields=["status", "updated_at"])
        token = self.preview().data["preview_token"]
        denied = self.post(self.publish_url, {"preview_token": token})
        self.assertEqual(denied.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Course.objects.count(), 0)

        self.lesson.status = "REVIEW"
        self.lesson.save(update_fields=["status", "updated_at"])
        review_token = self.preview().data["preview_token"]
        review_denied = self.post(self.publish_url, {"preview_token": review_token})
        self.assertEqual(review_denied.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Course.objects.count(), 0)

        self.lesson.status = "APPROVED"
        self.lesson.save(update_fields=["status", "updated_at"])
        token = self.preview().data["preview_token"]
        self.lesson.title = "Origem alterada"
        self.lesson.save(update_fields=["title", "updated_at"])
        self.assertIn("mudou", self.post(self.publish_url, {"preview_token": token}).data["detail"])

        token = self.preview().data["preview_token"]
        self.client.force_authenticate(self.other)
        self.assertEqual(self.post(self.publish_url, {"preview_token": token}).status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.user)
        ok = self.post(self.publish_url, {"preview_token": token})
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(self.post(self.publish_url, {"preview_token": token}).status_code, status.HTTP_409_CONFLICT)

    def test_non_staff_cannot_preview_or_publish(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.preview().status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.post(self.publish_url, {"preview_token": "00000000-0000-0000-0000-000000000000"}).status_code, status.HTTP_403_FORBIDDEN)
