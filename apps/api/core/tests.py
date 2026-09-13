import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, connection
from django.db.models.query import QuerySet
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    MAX_SUBMITTED_ANSWER_LENGTH,
    Certificate,
    Course,
    Exercise,
    ExerciseAttempt,
    Lesson,
    LessonProgress,
    Module,
    StudentProject,
    Enrollment,
    CourseProgress,
)
from core.services import (
    complete_course,
    create_exercise_attempt,
    recalculate_course_progress,
    resolve_learning_continuity,
)


class CourseModuleWriteAuthorizationApiTests(APITestCase):
    """Authorization through the real router, serializers and database."""

    @classmethod
    def setUpTestData(cls):
        cls.student = get_user_model().objects.create_user(
            email="write-student@example.com", username="write_student",
        )
        cls.staff = get_user_model().objects.create_user(
            email="write-staff@example.com", username="write_staff",
            is_staff=True, is_superuser=False,
        )
        cls.superuser = get_user_model().objects.create_user(
            email="write-superuser@example.com", username="write_superuser",
            is_staff=False, is_superuser=True,
        )
        cls.course = Course.objects.create(title="Authorization course", description="Test")
        cls.module = Module.objects.create(course=cls.course, title="Authorization module")

    def _resource(self, resource):
        if resource == "course":
            return Course, self.course, {"title": "New course", "description": "Test"}
        return Module, self.module, {"course": self.course.pk, "title": "New module"}

    def _assert_read_contract(self, resource):
        _, instance, _ = self._resource(resource)
        module_data = {
            "id": self.module.pk, "course": self.course.pk,
            "title": self.module.title, "order": 0, "lessons": [],
        }
        for role, user in (("anonymous", None), ("student", self.student)):
            self.client.force_authenticate(user)
            with self.subTest(role=role):
                list_url = reverse(f"{resource}-list")
                detail_url = reverse(f"{resource}-detail", kwargs={"pk": instance.pk})
                listing = self.client.get(list_url)
                detail = self.client.get(detail_url)
                self.assertEqual(listing.status_code, status.HTTP_200_OK)
                self.assertEqual(detail.status_code, status.HTTP_200_OK)
                self.assertEqual(set(listing.data), {"count", "next", "previous", "results"})
                self.assertEqual(listing.data["count"], 1)
                self.assertIsNone(listing.data["next"])
                self.assertIsNone(listing.data["previous"])
                self.assertEqual(listing.data["results"], [detail.data])
                if resource == "course":
                    self.assertEqual(set(detail.data), {"id", "title", "description", "created_at", "modules"})
                    self.assertEqual(detail.data["id"], self.course.pk)
                    self.assertEqual(detail.data["title"], self.course.title)
                    self.assertEqual(detail.data["description"], self.course.description)
                    self.assertTrue(detail.data["created_at"])
                    self.assertEqual(detail.data["modules"], [module_data])
                else:
                    self.assertEqual(detail.data, module_data)
                for url in (list_url, detail_url):
                    for method in ("head", "options"):
                        with self.subTest(url=url, method=method):
                            self.assertEqual(getattr(self.client, method)(url).status_code, status.HTTP_200_OK)

    def _assert_writes_denied(self, resource, user, expected):
        self.client.force_authenticate(user)
        _, instance, payload = self._resource(resource)
        before_courses = list(Course.objects.order_by("pk").values())
        before_modules = list(Module.objects.order_by("pk").values())
        for method in ("post", "patch", "delete"):
            with self.subTest(method=method):
                url = reverse(f"{resource}-list") if method == "post" else reverse(
                    f"{resource}-detail", kwargs={"pk": instance.pk},
                )
                response = getattr(self.client, method)(url, payload, format="json")
                self.assertEqual(response.status_code, expected, response.data)
                self.assertEqual(list(Course.objects.order_by("pk").values()), before_courses)
                self.assertEqual(list(Module.objects.order_by("pk").values()), before_modules)

    def _assert_administrative_writes(self, resource):
        model, _, payload = self._resource(resource)
        for role in ("staff", "superuser"):
            self.client.force_authenticate(getattr(self, role))
            with self.subTest(role=role):
                initial_count = model.objects.count()
                created = self.client.post(reverse(f"{resource}-list"), payload, format="json")
                self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
                saved = model.objects.get(pk=created.data["id"])
                self.assertEqual(saved.title, payload["title"])
                if resource == "course":
                    self.assertEqual(saved.description, payload["description"])
                else:
                    self.assertEqual(saved.course_id, payload["course"])
                    self.assertEqual(saved.order, 0)
                self.assertEqual(model.objects.count(), initial_count + 1)
                detail_url = reverse(f"{resource}-detail", kwargs={"pk": saved.pk})
                updated = self.client.patch(detail_url, {"title": "Updated"}, format="json")
                self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
                saved.refresh_from_db()
                self.assertEqual(saved.title, "Updated")
                self.assertEqual(model.objects.count(), initial_count + 1)
                deleted = self.client.delete(detail_url)
                self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
                self.assertFalse(model.objects.filter(pk=saved.pk).exists())
                self.assertEqual(model.objects.count(), initial_count)

    def test_course_read_contract(self):
        self._assert_read_contract("course")

    def test_module_read_contract(self):
        self._assert_read_contract("module")

    def test_course_anonymous_writes_denied(self):
        self._assert_writes_denied("course", None, status.HTTP_401_UNAUTHORIZED)

    def test_module_anonymous_writes_denied(self):
        self._assert_writes_denied("module", None, status.HTTP_401_UNAUTHORIZED)

    def test_course_student_writes_denied(self):
        self._assert_writes_denied("course", self.student, status.HTTP_403_FORBIDDEN)

    def test_module_student_writes_denied(self):
        self._assert_writes_denied("module", self.student, status.HTTP_403_FORBIDDEN)

    def test_course_administrative_writes_allowed(self):
        self._assert_administrative_writes("course")

    def test_module_administrative_writes_allowed(self):
        self._assert_administrative_writes("module")


class EnrollmentApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="student@example.com", username="student", password="password"
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com", username="other", password="password"
        )
        self.course = Course.objects.create(title="Engenharia de Dados", description="Teste")
        self.url = reverse("enrollment-list")

    def test_authenticated_user_creates_enrollment_without_user_id(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, {"course_id": self.course.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        enrollment = Enrollment.objects.get()
        self.assertEqual(enrollment.user, self.user)
        self.assertEqual(enrollment.status, Enrollment.STATUS_ACTIVE)
        self.assertNotIn("user", response.data)

    def test_duplicate_enrollment_is_idempotent(self):
        self.client.force_authenticate(self.user)
        first = self.client.post(self.url, {"course_id": self.course.id}, format="json")
        second = self.client.post(self.url, {"course_id": self.course.id}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_anonymous_user_cannot_access_enrollments(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(self.url, {"course_id": self.course.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_reads_only_own_enrollment(self):
        own = Enrollment.objects.create(user=self.user, course=self.course)
        other_course = Course.objects.create(title="Python", description="Teste")
        foreign = Enrollment.objects.create(user=self.other_user, course=other_course)
        self.client.force_authenticate(self.user)

        listing = self.client.get(self.url)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in listing.data["results"]], [own.id])
        self.assertEqual(
            self.client.get(reverse("enrollment-detail", kwargs={"pk": own.id})).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(reverse("enrollment-detail", kwargs={"pk": foreign.id})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_cannot_change_another_users_enrollment(self):
        foreign = Enrollment.objects.create(user=self.other_user, course=self.course)
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            reverse("enrollment-detail", kwargs={"pk": foreign.id}),
            {"status": Enrollment.STATUS_CANCELLED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, Enrollment.STATUS_ACTIVE)

    def test_cancel_and_reenroll_reuses_same_enrollment(self):
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)
        detail = reverse("enrollment-detail", kwargs={"pk": enrollment.id})
        cancelled = self.client.patch(detail, {"status": Enrollment.STATUS_CANCELLED}, format="json")
        reenrolled = self.client.post(self.url, {"course_id": self.course.id}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(reenrolled.status_code, status.HTTP_200_OK)
        self.assertEqual(reenrolled.data["id"], enrollment.id)
        self.assertEqual(reenrolled.data["status"], Enrollment.STATUS_ACTIVE)

    def test_enrolled_courses_contract(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("enrollment-courses"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id"], self.course.id)
        self.assertIn("modules", response.data["results"][0])


class CourseAccessApiTests(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            email="access-student@example.com",
            username="access_student",
            password="password",
        )
        self.staff = get_user_model().objects.create_user(
            email="staff@example.com",
            username="staff",
            password="password",
            is_staff=True,
        )
        self.course = Course.objects.create(title="Curso protegido", description="Teste")
        self.url = reverse("enrollment-access")

    def test_student_without_enrollment_has_no_course_access(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"access_type": "none", "courses": []})

    def test_enrolled_student_has_enrollment_access(self):
        Enrollment.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.data["access_type"], "enrollment")
        self.assertEqual([course["id"] for course in response.data["courses"]], [self.course.id])

    def test_staff_has_administrative_access_without_enrollment(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access_type"], "administrative")
        self.assertEqual([course["id"] for course in response.data["courses"]], [self.course.id])

    def test_administrative_access_does_not_create_enrollment(self):
        self.client.force_authenticate(self.staff)
        self.client.get(self.url)
        self.assertFalse(Enrollment.objects.filter(user=self.staff).exists())

    def test_common_user_cannot_request_administrative_exception(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(f"{self.url}?administrative=true")
        self.assertEqual(response.data["access_type"], "none")
        self.assertEqual(response.data["courses"], [])


class CourseProgressApiTests(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            email="progress@example.com", username="progress", password="password"
        )
        self.other_student = get_user_model().objects.create_user(
            email="other-progress@example.com", username="other_progress", password="password"
        )
        self.admin = get_user_model().objects.create_user(
            email="progress-admin@example.com",
            username="progress_admin",
            password="password",
            is_staff=True,
        )
        self.course = Course.objects.create(title="Progresso Seguro", description="Teste")
        self.enrollment = Enrollment.objects.create(user=self.student, course=self.course)
        self.list_url = reverse("course-progress-list")
        self.course_url = reverse(
            "course-progress-by-course", kwargs={"course_id": self.course.id}
        )

    def test_list_safely_creates_default_progress_for_active_enrollment(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["percentage"], "0.00")
        self.assertEqual(response.data["results"][0]["academic_state"], "not_started")
        self.assertIsNone(response.data["results"][0]["first_activity_at"])
        self.assertEqual(CourseProgress.objects.get().enrollment, self.enrollment)

    def test_student_can_read_progress_for_own_course(self):
        progress = CourseProgress.objects.create(enrollment=self.enrollment)
        self.client.force_authenticate(self.student)
        response = self.client.get(self.course_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], progress.id)
        self.assertEqual(response.data["course"]["id"], self.course.id)

    def test_progress_is_isolated_between_users(self):
        CourseProgress.objects.create(enrollment=self.enrollment)
        other_enrollment = Enrollment.objects.create(user=self.other_student, course=self.course)
        other_progress = CourseProgress.objects.create(enrollment=other_enrollment)
        self.client.force_authenticate(self.student)
        listing = self.client.get(self.list_url)
        self.assertEqual(len(listing.data["results"]), 1)
        self.assertNotEqual(listing.data["results"][0]["id"], other_progress.id)
        self.assertEqual(
            self.client.get(reverse("course-progress-detail", kwargs={"pk": other_progress.id})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_user_cannot_read_progress(self):
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_course_without_enrollment_has_no_progress_access(self):
        course = Course.objects.create(title="Sem matrícula", description="Teste")
        self.client.force_authenticate(self.student)
        response = self.client.get(
            reverse("course-progress-by-course", kwargs={"course_id": course.id})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancelled_enrollment_has_no_progress_access(self):
        self.enrollment.status = Enrollment.STATUS_CANCELLED
        self.enrollment.save(update_fields=["status", "updated_at"])
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(self.course_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(CourseProgress.objects.exists())

    def test_repeated_reads_do_not_duplicate_progress(self):
        self.client.force_authenticate(self.student)
        first = self.client.get(self.course_url)
        second = self.client.get(self.course_url)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(CourseProgress.objects.count(), 1)

    def test_frontend_cannot_set_percentage(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            self.list_url,
            {"enrollment": self.enrollment.id, "percentage": 100},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(CourseProgress.objects.exists())

    def test_admin_course_access_does_not_generate_academic_progress(self):
        self.client.force_authenticate(self.admin)
        access = self.client.get(reverse("enrollment-access"))
        progress = self.client.get(self.list_url)
        self.assertEqual(access.data["access_type"], "administrative")
        self.assertEqual(progress.data["results"], [])
        self.assertFalse(CourseProgress.objects.filter(enrollment__user=self.admin).exists())

    def test_existing_enrollment_contract_remains_compatible(self):
        self.client.force_authenticate(self.student)
        enrollment_response = self.client.get(reverse("enrollment-list"))
        progress_response = self.client.get(self.course_url)
        self.assertEqual(enrollment_response.data["results"][0]["id"], self.enrollment.id)
        self.assertEqual(progress_response.data["enrollment"], self.enrollment.id)


class LessonProgressApiTests(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            email="lesson-progress@example.com", username="lesson_progress", password="password"
        )
        self.other_student = get_user_model().objects.create_user(
            email="other-lesson-progress@example.com",
            username="other_lesson_progress",
            password="password",
        )
        self.admin = get_user_model().objects.create_user(
            email="lesson-admin@example.com",
            username="lesson_admin",
            password="password",
            is_staff=True,
        )
        self.course = Course.objects.create(title="Curso por aula", description="Teste")
        self.module = Module.objects.create(course=self.course, title="Módulo", order=1)
        self.lesson = Lesson.objects.create(
            module=self.module, title="Aula 1", content_type="ARTICLE", order=1
        )
        self.second_lesson = Lesson.objects.create(
            module=self.module, title="Aula 2", content_type="ARTICLE", order=2
        )
        self.enrollment = Enrollment.objects.create(user=self.student, course=self.course)
        self.start_url = reverse("lesson-progress-start", kwargs={"lesson_id": self.lesson.id})
        self.complete_url = reverse("lesson-progress-complete", kwargs={"lesson_id": self.lesson.id})
        self.list_url = reverse("lesson-progress-list")

    def test_start_safely_creates_lesson_and_course_progress(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(self.start_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress = LessonProgress.objects.get()
        self.assertEqual(progress.course_progress.enrollment, self.enrollment)
        self.assertEqual(progress.lesson, self.lesson)
        self.assertNotIn("user", response.data)

    def test_start_transitions_to_in_progress(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(self.start_url, {}, format="json")
        self.assertEqual(response.data["status"], LessonProgress.STATUS_IN_PROGRESS)
        self.assertIsNotNone(response.data["started_at"])

    def test_start_is_idempotent_without_duplicate_or_started_at_reset(self):
        self.client.force_authenticate(self.student)
        first = self.client.post(self.start_url, {}, format="json")
        second = self.client.post(self.start_url, {}, format="json")
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(first.data["started_at"], second.data["started_at"])
        self.assertEqual(LessonProgress.objects.count(), 1)

    def test_complete_requires_start_and_transitions_to_completed(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(
            self.client.post(self.complete_url, {}, format="json").status_code,
            status.HTTP_409_CONFLICT,
        )
        self.client.post(self.start_url, {}, format="json")
        response = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(response.data["status"], LessonProgress.STATUS_COMPLETED)
        self.assertIsNotNone(response.data["completed_at"])

    def test_complete_is_idempotent_without_timestamp_reset(self):
        self.client.force_authenticate(self.student)
        self.client.post(self.start_url, {}, format="json")
        first = self.client.post(self.complete_url, {}, format="json")
        second = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(first.data["completed_at"], second.data["completed_at"])
        self.assertEqual(LessonProgress.objects.count(), 1)

    def test_progress_is_isolated_between_users(self):
        self.client.force_authenticate(self.student)
        own = self.client.post(self.start_url, {}, format="json")
        self.client.force_authenticate(self.other_student)
        self.assertEqual(self.client.get(self.list_url).data["results"], [])
        self.assertEqual(
            self.client.get(reverse("lesson-progress-detail", kwargs={"pk": own.data["id"]})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_missing_or_cancelled_enrollment_blocks_activity(self):
        self.client.force_authenticate(self.other_student)
        self.assertEqual(self.client.post(self.start_url, {}, format="json").status_code, 404)
        self.enrollment.status = Enrollment.STATUS_CANCELLED
        self.enrollment.save(update_fields=["status", "updated_at"])
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.post(self.start_url, {}, format="json").status_code, 404)
        self.assertFalse(LessonProgress.objects.exists())

    def test_lesson_from_another_course_is_rejected(self):
        other_course = Course.objects.create(title="Outro curso", description="Teste")
        other_module = Module.objects.create(course=other_course, title="Outro módulo", order=1)
        other_lesson = Lesson.objects.create(
            module=other_module, title="Outra aula", content_type="ARTICLE", order=1
        )
        self.client.force_authenticate(self.student)
        response = self.client.post(
            reverse("lesson-progress-start", kwargs={"lesson_id": other_lesson.id}),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(LessonProgress.objects.exists())

    def test_admin_access_does_not_create_academic_progress(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(reverse("enrollment-access")).data["access_type"], "administrative")
        self.assertEqual(self.client.post(self.start_url, {}, format="json").status_code, 404)
        self.assertFalse(CourseProgress.objects.filter(enrollment__user=self.admin).exists())
        self.assertFalse(LessonProgress.objects.exists())

    def test_activity_updates_lesson_and_course_timestamps(self):
        self.client.force_authenticate(self.student)
        self.client.post(self.start_url, {}, format="json")
        lesson_progress = LessonProgress.objects.get()
        course_progress = lesson_progress.course_progress
        self.assertIsNotNone(lesson_progress.last_activity_at)
        self.assertEqual(course_progress.first_activity_at, lesson_progress.started_at)
        self.assertEqual(course_progress.last_activity_at, lesson_progress.last_activity_at)

        previous_activity = lesson_progress.last_activity_at
        self.client.post(self.complete_url, {}, format="json")
        lesson_progress.refresh_from_db()
        course_progress.refresh_from_db()
        self.assertGreaterEqual(lesson_progress.last_activity_at, previous_activity)
        self.assertEqual(course_progress.last_activity_at, lesson_progress.last_activity_at)

    def test_course_percentage_is_derived_from_completed_lessons(self):
        self.client.force_authenticate(self.student)
        self.client.post(self.start_url, {}, format="json")
        first = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(first.data["course_progress_percentage"], "50.00")

        second_start = reverse("lesson-progress-start", kwargs={"lesson_id": self.second_lesson.id})
        second_complete = reverse("lesson-progress-complete", kwargs={"lesson_id": self.second_lesson.id})
        self.client.post(second_start, {}, format="json")
        second = self.client.post(second_complete, {}, format="json")
        course_progress = CourseProgress.objects.get(enrollment=self.enrollment)
        self.assertEqual(second.data["course_progress_percentage"], "100.00")
        self.assertEqual(course_progress.academic_state, CourseProgress.STATE_IN_PROGRESS)
        self.assertFalse(Certificate.objects.filter(user=self.student, course=self.course).exists())

    def test_course_without_lessons_recalculates_to_zero(self):
        empty_course = Course.objects.create(title="Curso vazio", description="Teste")
        enrollment = Enrollment.objects.create(user=self.student, course=empty_course)
        course_progress = CourseProgress.objects.create(enrollment=enrollment, percentage=75)
        recalculate_course_progress(course_progress)
        course_progress.refresh_from_db()
        self.assertEqual(str(course_progress.percentage), "0.00")

    def test_direct_state_and_percentage_manipulation_is_rejected(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(
            self.client.post(
                self.list_url,
                {"status": "completed", "percentage": 100},
                format="json",
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        response = self.client.post(
            self.start_url,
            {"status": "completed", "percentage": 100},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(LessonProgress.objects.exists())

    def test_unauthenticated_endpoints_are_rejected(self):
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.start_url, {}, format="json").status_code, 401)
        self.assertEqual(self.client.post(self.complete_url, {}, format="json").status_code, 401)


class CourseCompletionAndContinuityTests(APITestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            email="continuity@example.com", username="continuity", password="password"
        )
        self.other = get_user_model().objects.create_user(
            email="other-continuity@example.com", username="other_continuity", password="password"
        )
        self.admin = get_user_model().objects.create_user(
            email="admin-continuity@example.com", username="admin_continuity", password="password", is_staff=True
        )
        self.course = Course.objects.create(title="Jornada", description="Teste")
        later_module = Module.objects.create(course=self.course, title="Módulo 2", order=2)
        first_module = Module.objects.create(course=self.course, title="Módulo 1", order=1)
        self.first_lesson = Lesson.objects.create(
            module=first_module, title="Aula 1", content_type="ARTICLE", order=1
        )
        self.second_lesson = Lesson.objects.create(
            module=first_module, title="Aula 2", content_type="ARTICLE", order=2
        )
        self.third_lesson = Lesson.objects.create(
            module=later_module, title="Aula 3", content_type="ARTICLE", order=1
        )
        self.enrollment = Enrollment.objects.create(user=self.student, course=self.course)
        self.progress = CourseProgress.objects.create(enrollment=self.enrollment)
        self.complete_url = reverse("course-progress-complete", kwargs={"course_id": self.course.id})
        self.continue_url = reverse("learning-continuity")

    def finish_lesson(self, lesson):
        now = timezone.now()
        return LessonProgress.objects.create(
            course_progress=self.progress,
            lesson=lesson,
            status=LessonProgress.STATUS_COMPLETED,
            started_at=now,
            last_activity_at=now,
            completed_at=now,
        )

    def test_incomplete_course_cannot_complete_and_client_fields_are_rejected(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        spoofed = self.client.post(
            self.complete_url,
            {"academic_state": "completed", "percentage": 100, "completed_at": timezone.now()},
            format="json",
        )
        self.assertEqual(spoofed.status_code, status.HTTP_400_BAD_REQUEST)
        self.progress.refresh_from_db()
        self.assertNotEqual(self.progress.academic_state, CourseProgress.STATE_COMPLETED)

    def test_all_lessons_make_course_eligible_but_do_not_complete_implicitly(self):
        for lesson in (self.first_lesson, self.second_lesson, self.third_lesson):
            self.finish_lesson(lesson)
        recalculate_course_progress(self.progress)
        self.progress.refresh_from_db()
        self.assertEqual(self.progress.percentage, 100)
        self.assertEqual(self.progress.academic_state, CourseProgress.STATE_IN_PROGRESS)

        completed, created = complete_course(user=self.student, course_id=self.course.id)
        self.assertTrue(created)
        self.assertEqual(completed.academic_state, CourseProgress.STATE_COMPLETED)
        self.assertIsNotNone(completed.completed_at)
        self.assertFalse(Certificate.objects.filter(user=self.student, course=self.course).exists())

    def test_completion_endpoint_persists_and_is_idempotent(self):
        for lesson in (self.first_lesson, self.second_lesson, self.third_lesson):
            self.finish_lesson(lesson)
        recalculate_course_progress(self.progress)
        self.client.force_authenticate(self.student)
        first = self.client.post(self.complete_url, {}, format="json")
        second = self.client.post(self.complete_url, {}, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["academic_state"], "completed")
        self.assertEqual(first.data["completed_at"], second.data["completed_at"])

    def test_cancelled_foreign_and_admin_enrollments_cannot_complete(self):
        self.enrollment.status = Enrollment.STATUS_CANCELLED
        self.enrollment.save(update_fields=["status", "updated_at"])
        for user in (self.student, self.other, self.admin):
            with self.subTest(user=user.email):
                self.client.force_authenticate(user)
                self.assertEqual(self.client.post(self.complete_url, {}, format="json").status_code, 404)
        self.assertFalse(Enrollment.objects.filter(user=self.admin).exists())

    def test_new_student_starts_at_first_pedagogical_lesson(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(self.continue_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["type"], "start_course")
        self.assertEqual(response.data["lesson"]["id"], self.first_lesson.id)

    def test_in_progress_lesson_is_resumed_and_completed_lesson_advances(self):
        in_progress = LessonProgress.objects.create(
            course_progress=self.progress,
            lesson=self.second_lesson,
            status=LessonProgress.STATUS_IN_PROGRESS,
            started_at=timezone.now(),
            last_activity_at=timezone.now(),
        )
        step = resolve_learning_continuity(user=self.student)
        self.assertEqual((step["type"], step["lesson"].id), ("continue_lesson", self.second_lesson.id))
        in_progress.delete()
        self.finish_lesson(self.first_lesson)
        step = resolve_learning_continuity(user=self.student)
        self.assertEqual((step["type"], step["lesson"].id), ("next_lesson", self.second_lesson.id))

    def test_all_lessons_wait_for_explicit_completion_then_stop_repeating_lessons(self):
        for lesson in (self.first_lesson, self.second_lesson, self.third_lesson):
            self.finish_lesson(lesson)
        recalculate_course_progress(self.progress)
        self.assertEqual(resolve_learning_continuity(user=self.student)["type"], "complete_course")
        complete_course(user=self.student, course_id=self.course.id)
        self.assertEqual(resolve_learning_continuity(user=self.student)["type"], "course_completed")

    def test_cancelled_admin_and_other_users_receive_no_academic_continuity(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.continue_url).data["type"], "no_enrollment")
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.continue_url).data["type"], "administrative")
        self.enrollment.status = Enrollment.STATUS_CANCELLED
        self.enrollment.save(update_fields=["status", "updated_at"])
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(self.continue_url).data["type"], "no_enrollment")

    def test_most_recent_course_wins_without_mixing_progress(self):
        other_course = Course.objects.create(title="Curso recente", description="Teste")
        module = Module.objects.create(course=other_course, title="Novo módulo", order=1)
        lesson = Lesson.objects.create(module=module, title="Nova aula", content_type="ARTICLE", order=1)
        enrollment = Enrollment.objects.create(user=self.student, course=other_course)
        recent = CourseProgress.objects.create(
            enrollment=enrollment,
            academic_state=CourseProgress.STATE_IN_PROGRESS,
            first_activity_at=timezone.now(),
            last_activity_at=timezone.now(),
        )
        LessonProgress.objects.create(
            course_progress=recent,
            lesson=lesson,
            status=LessonProgress.STATUS_IN_PROGRESS,
            started_at=timezone.now(),
            last_activity_at=timezone.now(),
        )
        self.client.force_authenticate(self.student)
        response = self.client.get(self.continue_url)
        self.assertEqual(response.data["course"]["id"], other_course.id)
        self.assertEqual(response.data["lesson"]["id"], lesson.id)


class AuthenticationFlowTests(APITestCase):
    def test_user_can_register_and_login_with_email(self):
        credentials = {
            "email": "login-local@example.com",
            "username": "login_local",
            "password1": "Dojo-local-test-2026!",
            "password2": "Dojo-local-test-2026!",
        }

        registration = self.client.post(
            "/api/auth/registration/", credentials, format="json"
        )
        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)

        login = self.client.post(
            "/api/auth/login/",
            {
                "username": credentials["email"],
                "email": credentials["email"],
                "password": credentials["password1"],
            },
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertTrue(login.data["key"])


class AdministrativeProfileContractTests(APITestCase):
    def test_administrative_flags_are_exposed_but_read_only(self):
        user = get_user_model().objects.create_user(
            email="profile-admin@example.com",
            username="profile_admin",
            password="password",
            is_staff=True,
            is_superuser=False,
        )
        self.client.force_authenticate(user)
        profile_url = reverse("user-profile")
        response = self.client.get(profile_url)
        self.assertTrue(response.data["is_staff"])
        self.assertFalse(response.data["is_superuser"])

        update = self.client.patch(
            profile_url,
            {"is_staff": False, "is_superuser": True},
            format="json",
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)


class CoreApiTests(APITestCase):
    def test_course_list_returns_ok(self):
        Course.objects.create(title="Curso Base", description="Teste")
        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertTrue(any(course["title"] == "Curso Base" for course in results))

    def test_exercise_evaluation_for_sql_answers(self):
        course = Course.objects.create(title="SQL", description="Teste")
        module = Module.objects.create(course=course, title="Fundamentos", order=1)
        lesson = Lesson.objects.create(
            module=module,
            title="Lição 1",
            content_type="LAB",
            order=1,
        )
        exercise = Exercise.objects.create(
            lesson=lesson,
            title="Exercício 1",
            statement="Selecione os clientes",
            answer_type="SQL",
            expected_answer="SELECT name FROM customers",
            expected_keywords=["SELECT", "FROM"],
            evaluation_mode="keywords",
            points=100,
        )

        self.assertTrue(exercise.evaluate_answer("SELECT name FROM customers"))
        self.assertFalse(exercise.evaluate_answer("FROM customers"))

    def test_course_api_exposes_nested_lesson_and_exercise(self):
        course = Course.objects.create(title="SQL", description="Teste")
        module = Module.objects.create(course=course, title="Fundamentos", order=1)
        lesson = Lesson.objects.create(
            module=module,
            title="Lição 1",
            content_type="LAB",
            order=1,
        )
        Exercise.objects.create(
            lesson=lesson,
            title="Exercício 1",
            statement="Selecione os clientes",
            answer_type="SQL",
            expected_answer="SELECT name FROM customers",
            expected_keywords=["SELECT", "FROM"],
            evaluation_mode="keywords",
            points=100,
        )

        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = next(item for item in response.data["results"] if item["title"] == "SQL")
        self.assertEqual(
            payload["modules"][0]["lessons"][0]["exercise"]["title"],
            "Exercício 1",
        )
        public_exercise = payload["modules"][0]["lessons"][0]["exercise"]
        self.assertNotIn("expected_answer", public_exercise)
        self.assertNotIn("expected_keywords", public_exercise)
        self.assertNotIn("evaluation_mode", public_exercise)
        self.assertEqual(public_exercise["submission"]["format"], "text")


class ExerciseEvaluationTests(APITestCase):
    def setUp(self):
        course = Course.objects.create(title="Avaliação", description="Teste")
        module = Module.objects.create(course=course, title="Módulo", order=1)
        lesson = Lesson.objects.create(
            module=module, title="Lição", content_type="LAB", order=1
        )
        self.exercise = Exercise.objects.create(
            lesson=lesson,
            title="Exercício",
            statement="Responda",
            expected_answer="SELECT name FROM customers",
            expected_keywords=["SELECT", "FROM"],
            evaluation_mode="keywords",
        )

    def test_rejects_invalid_empty_and_whitespace_answers(self):
        self.assertFalse(self.exercise.evaluate_answer(None))
        self.assertFalse(self.exercise.evaluate_answer(123))
        self.assertFalse(self.exercise.evaluate_answer(""))
        self.assertFalse(self.exercise.evaluate_answer("   \n"))

    def test_exact_mode_accepts_only_normalized_exact_answer(self):
        self.exercise.evaluation_mode = "exact"
        self.assertTrue(
            self.exercise.evaluate_answer("  SELECT name\nFROM customers  ")
        )
        self.assertFalse(self.exercise.evaluate_answer("SELECT name FROM other"))

    def test_contains_mode_accepts_expected_text_only_when_present(self):
        self.exercise.evaluation_mode = "contains"
        self.assertTrue(
            self.exercise.evaluate_answer("EXPLAIN SELECT name FROM customers")
        )
        self.assertFalse(self.exercise.evaluate_answer("SELECT id FROM customers"))

    def test_keywords_mode_requires_every_keyword(self):
        self.assertTrue(self.exercise.evaluate_answer("select name from customers"))
        self.assertFalse(self.exercise.evaluate_answer("select name"))

    def test_invalid_evaluation_mode_fails_closed(self):
        self.exercise.evaluation_mode = "unsupported"
        with self.assertRaises(ValueError):
            self.exercise.evaluate_answer("anything")


class ExerciseAttemptApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="attempt@example.com", username="attempt", password="password"
        )
        self.other_user = get_user_model().objects.create_user(
            email="other-attempt@example.com",
            username="other_attempt",
            password="password",
        )
        self.course = Course.objects.create(title="Tentativas", description="Teste")
        module = Module.objects.create(course=self.course, title="Módulo", order=1)
        self.lesson = Lesson.objects.create(
            module=module, title="Lição", content_type="LAB", order=1
        )
        self.exercise = Exercise.objects.create(
            lesson=self.lesson,
            title="Exercício",
            statement="Responda",
            expected_answer="SELECT name FROM customers",
            expected_keywords=["SELECT", "FROM"],
            evaluation_mode="keywords",
        )
        self.url = reverse(
            "exercise-attempt-list", kwargs={"exercise_id": self.exercise.id}
        )
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)

    def payload(self, answer="SELECT name FROM customers", key=None):
        return {
            "submitted_answer": answer,
            "idempotency_key": str(key or uuid.uuid4()),
        }

    def test_anonymous_user_cannot_submit(self):
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_creates_own_server_evaluated_attempt(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attempt = ExerciseAttempt.objects.get()
        self.assertEqual(attempt.user, self.user)
        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(response.data["feedback"]["code"], "accepted")
        self.assertNotIn("submitted_answer", response.data)
        self.assertNotIn("expected_answer", response.data)
        self.assertNotIn("expected_keywords", response.data)

    def test_exercise_does_not_exist(self):
        self.client.force_authenticate(self.user)
        url = reverse("exercise-attempt-list", kwargs={"exercise_id": 999999})
        response = self.client.post(url, self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rejects_missing_invalid_empty_and_oversized_answers(self):
        self.client.force_authenticate(self.user)
        key = str(uuid.uuid4())
        cases = [
            {"idempotency_key": key},
            {"submitted_answer": 123, "idempotency_key": key},
            {"submitted_answer": "", "idempotency_key": key},
            {"submitted_answer": "  \n", "idempotency_key": key},
            {
                "submitted_answer": "x" * (MAX_SUBMITTED_ANSWER_LENGTH + 1),
                "idempotency_key": key,
            },
        ]
        for payload in cases:
            with self.subTest(payload_type=type(payload.get("submitted_answer"))):
                response = self.client.post(self.url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ExerciseAttempt.objects.exists())

    def test_accepts_answer_at_maximum_length(self):
        self.exercise.expected_answer = "x" * MAX_SUBMITTED_ANSWER_LENGTH
        self.exercise.expected_keywords = []
        self.exercise.evaluation_mode = "exact"
        self.exercise.save()
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.url,
            self.payload("x" * MAX_SUBMITTED_ANSWER_LENGTH),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["passed"])

    def test_incorrect_answer_is_persisted_without_approval(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self.payload("DROP TABLE users"), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["passed"])
        self.assertEqual(response.data["feedback"]["code"], "not_accepted")

    def test_invalid_configuration_is_persisted_as_safe_failure(self):
        self.exercise.evaluation_mode = "invalid"
        self.exercise.save(update_fields=["evaluation_mode"])
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["passed"])
        self.assertEqual(response.data["feedback"]["code"], "evaluation_unavailable")
        self.assertNotContains(response, "invalid", status_code=status.HTTP_201_CREATED)

    def test_attempt_numbers_increment_and_history_is_descending(self):
        self.client.force_authenticate(self.user)
        first = self.client.post(self.url, self.payload("wrong"), format="json")
        second = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(first.data["attempt_number"], 1)
        self.assertEqual(second.data["attempt_number"], 2)
        history = self.client.get(self.url)
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["attempt_number"] for item in history.data["results"]],
            [2, 1],
        )

    def test_history_is_owned_by_authenticated_user(self):
        ExerciseAttempt.objects.create(
            user=self.other_user,
            exercise=self.exercise,
            idempotency_key=uuid.uuid4(),
            submitted_answer="private answer",
            attempt_number=1,
            passed=False,
            feedback={"code": "not_accepted", "message": "Tente novamente."},
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_client_cannot_spoof_server_owned_fields(self):
        self.client.force_authenticate(self.user)
        payload = self.payload("wrong") | {
            "user": self.other_user.id,
            "passed": True,
            "feedback": {"code": "accepted", "message": "fake"},
            "attempt_number": 99,
            "evaluation_version": "attacker",
            "correct": True,
            "score": 999,
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attempt = ExerciseAttempt.objects.get()
        self.assertEqual(attempt.user, self.user)
        self.assertFalse(attempt.passed)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.evaluation_version, "v1")

    def test_active_enrollment_is_required_in_the_exercise_course(self):
        self.enrollment.status = Enrollment.STATUS_CANCELLED
        self.enrollment.save(update_fields=["status"])
        self.client.force_authenticate(self.user)

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ExerciseAttempt.objects.exists())

    def test_enrollment_in_another_course_does_not_grant_access(self):
        self.enrollment.delete()
        other_course = Course.objects.create(title="Outro curso", description="Teste")
        Enrollment.objects.create(user=self.user, course=other_course)
        self.client.force_authenticate(self.user)

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ExerciseAttempt.objects.exists())

    def test_administrative_access_does_not_create_academic_attempt(self):
        admin = get_user_model().objects.create_user(
            email="attempt-admin@example.com",
            username="attempt_admin",
            password="password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(admin)

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ExerciseAttempt.objects.filter(user=admin).exists())
        self.assertFalse(Enrollment.objects.filter(user=admin).exists())

    def test_attempt_records_activity_without_completing_lesson_or_course(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        course_progress = CourseProgress.objects.get(enrollment=self.enrollment)
        lesson_progress = LessonProgress.objects.get(
            course_progress=course_progress,
            lesson=self.lesson,
        )
        attempt = ExerciseAttempt.objects.get()
        self.assertEqual(lesson_progress.status, LessonProgress.STATUS_IN_PROGRESS)
        self.assertEqual(lesson_progress.started_at, attempt.created_at)
        self.assertEqual(lesson_progress.last_activity_at, attempt.created_at)
        self.assertIsNone(lesson_progress.completed_at)
        self.assertEqual(course_progress.academic_state, CourseProgress.STATE_IN_PROGRESS)
        self.assertEqual(course_progress.first_activity_at, attempt.created_at)
        self.assertEqual(course_progress.last_activity_at, attempt.created_at)
        self.assertEqual(course_progress.percentage, 0)
        self.assertFalse(Certificate.objects.filter(user=self.user).exists())

    def test_attempt_updates_existing_activity_timestamps(self):
        course_progress = CourseProgress.objects.create(enrollment=self.enrollment)
        lesson_progress = LessonProgress.objects.create(
            course_progress=course_progress,
            lesson=self.lesson,
            status=LessonProgress.STATUS_IN_PROGRESS,
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(self.url, self.payload(), format="json")

        lesson_progress.refresh_from_db()
        course_progress.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(lesson_progress.last_activity_at, ExerciseAttempt.objects.get().created_at)
        self.assertEqual(course_progress.last_activity_at, ExerciseAttempt.objects.get().created_at)

    def test_evidence_reports_history_best_latest_and_supported_filters(self):
        self.client.force_authenticate(self.user)
        first = self.client.post(self.url, self.payload("wrong"), format="json")
        second = self.client.post(self.url, self.payload(), format="json")
        evidence_url = reverse("exercise-evidence-list")

        for query in (
            f"?exercise={self.exercise.id}",
            f"?lesson={self.lesson.id}",
            f"?course={self.course.id}",
            f"?enrollment={self.enrollment.id}",
        ):
            with self.subTest(query=query):
                response = self.client.get(evidence_url + query)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 1)
                item = response.data[0]
                self.assertEqual(item["attempt_count"], 2)
                self.assertTrue(item["best_passed"])
                self.assertEqual(item["latest_attempt"]["id"], second.data["id"])
                self.assertNotEqual(item["latest_attempt"]["id"], first.data["id"])
                self.assertNotIn("submitted_answer", item["latest_attempt"])

    def test_evidence_is_isolated_and_foreign_enrollment_filter_returns_empty(self):
        self.client.force_authenticate(self.user)
        self.client.post(self.url, self.payload(), format="json")
        foreign_enrollment = Enrollment.objects.create(
            user=self.other_user,
            course=self.course,
        )

        response = self.client.get(
            reverse("exercise-evidence-list") + f"?enrollment={foreign_enrollment.id}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_idempotent_replay_returns_same_attempt_without_duplicate(self):
        self.client.force_authenticate(self.user)
        key = uuid.uuid4()
        payload = self.payload(key=key)
        first = self.client.post(self.url, payload, format="json")
        replay = self.client.post(self.url, payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(replay.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(ExerciseAttempt.objects.count(), 1)

    def test_idempotency_key_with_different_payload_conflicts(self):
        self.client.force_authenticate(self.user)
        key = uuid.uuid4()
        self.client.post(self.url, self.payload(key=key), format="json")
        conflict = self.client.post(
            self.url, self.payload("different", key=key), format="json"
        )
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(ExerciseAttempt.objects.count(), 1)

    def test_same_idempotency_key_cannot_be_reused_for_another_exercise(self):
        other_lesson = Lesson.objects.create(
            module=self.exercise.lesson.module,
            title="Outra lição",
            content_type="LAB",
            order=2,
        )
        other_exercise = Exercise.objects.create(
            lesson=other_lesson,
            title="Outro exercício",
            statement="Responda novamente",
            expected_answer="SELECT name FROM customers",
            expected_keywords=["SELECT", "FROM"],
            evaluation_mode="keywords",
        )
        other_url = reverse(
            "exercise-attempt-list", kwargs={"exercise_id": other_exercise.id}
        )
        key = uuid.uuid4()
        self.client.force_authenticate(self.user)

        first = self.client.post(self.url, self.payload(key=key), format="json")
        conflict = self.client.post(other_url, self.payload(key=key), format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(ExerciseAttempt.objects.count(), 1)

    def test_unrelated_integrity_error_is_not_misreported_as_concurrency(self):
        self.client.force_authenticate(self.user)
        with patch(
            "core.services.ExerciseAttempt.objects.create",
            side_effect=IntegrityError("unrelated database constraint"),
        ):
            with self.assertRaises(IntegrityError):
                create_exercise_attempt(
                    user=self.user,
                    exercise_id=self.exercise.id,
                    idempotency_key=uuid.uuid4(),
                    submitted_answer="SELECT name FROM customers",
                )


@skipUnless(
    connection.vendor == "postgresql",
    "requires PostgreSQL for real concurrent transaction coverage",
)
class ExerciseAttemptPostgreSQLConcurrencyTests(TransactionTestCase):
    """Exercise the production constraints with independent DB connections."""

    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="concurrent@example.com",
            username="concurrent",
            password="password",
        )
        course = Course.objects.create(title="Concorrência", description="Teste")
        module = Module.objects.create(course=course, title="Módulo", order=1)
        lesson = Lesson.objects.create(
            module=module,
            title="Lição",
            content_type="LAB",
            order=1,
        )
        self.exercise = Exercise.objects.create(
            lesson=lesson,
            title="Exercício",
            statement="Responda",
            expected_answer="SELECT name FROM customers",
            expected_keywords=["SELECT", "FROM"],
            evaluation_mode="keywords",
        )
        enrollment = Enrollment.objects.create(user=self.user, course=course)
        CourseProgress.objects.create(enrollment=enrollment)

    def _submit_concurrently(self, idempotency_keys):
        barrier = threading.Barrier(2)
        thread_state = threading.local()
        original_aggregate = QuerySet.aggregate

        def synchronized_aggregate(queryset, *args, **kwargs):
            result = original_aggregate(queryset, *args, **kwargs)
            if (
                queryset.model is ExerciseAttempt
                and not getattr(thread_state, "synchronized", False)
            ):
                thread_state.synchronized = True
                barrier.wait(timeout=10)
            return result

        def worker(idempotency_key):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_pid = cursor.fetchone()[0]
                user = get_user_model().objects.get(pk=self.user.pk)
                attempt, created = create_exercise_attempt(
                    user=user,
                    exercise_id=self.exercise.pk,
                    idempotency_key=idempotency_key,
                    submitted_answer="SELECT name FROM customers",
                )
                return attempt.pk, attempt.attempt_number, created, backend_pid
            finally:
                close_old_connections()

        with patch.object(QuerySet, "aggregate", new=synchronized_aggregate):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(worker, key) for key in idempotency_keys]
                results = [future.result(timeout=20) for future in futures]

        self.assertEqual(len({result[3] for result in results}), 2)
        return results

    def test_concurrent_distinct_keys_receive_distinct_attempt_numbers(self):
        results = self._submit_concurrently([uuid.uuid4(), uuid.uuid4()])

        self.assertEqual(ExerciseAttempt.objects.count(), 2)
        self.assertEqual({result[1] for result in results}, {1, 2})
        self.assertTrue(all(result[2] for result in results))
        self.assertEqual(
            ExerciseAttempt.objects.values("user", "exercise", "attempt_number")
            .distinct()
            .count(),
            2,
        )

    def test_concurrent_same_key_converges_to_idempotent_replay(self):
        key = uuid.uuid4()
        results = self._submit_concurrently([key, key])

        self.assertEqual(ExerciseAttempt.objects.filter(idempotency_key=key).count(), 1)
        self.assertEqual(len({result[0] for result in results}), 1)
        self.assertEqual(sorted(result[2] for result in results), [False, True])


class StudentProjectApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="student@example.com", username="student", password="dojo-test-password",
            github_url="https://github.com/student", linkedin_url="https://linkedin.com/in/student",
        )
        self.course = Course.objects.create(title="Formação em Dados", description="Teste")

    def test_student_can_publish_project_linked_to_course(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("student-project-list"),
            {
                "course": self.course.id,
                "title": "Análise de vendas",
                "summary": "Projeto desenvolvido durante a formação.",
                "technologies": ["Python", "Power BI"],
                "repository_url": "https://github.com/example/project",
                "status": "published",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["student"]["username"], "student")
        self.assertEqual(response.data["student"]["github_url"], "https://github.com/student")
        self.assertEqual(response.data["course_title"], "Formação em Dados")

    def test_public_sees_published_projects_but_not_drafts(self):
        StudentProject.objects.create(user=self.user, course=self.course, title="Publicado", summary="Visível", status="published")
        StudentProject.objects.create(user=self.user, course=self.course, title="Rascunho", summary="Privado", status="draft")
        response = self.client.get(reverse("student-project-list"))
        titles = [project["title"] for project in response.data["results"]]
        self.assertIn("Publicado", titles)
        self.assertNotIn("Rascunho", titles)

    def test_student_cannot_edit_another_students_project(self):
        other = get_user_model().objects.create_user(
            email="other@example.com", username="other", password="dojo-test-password"
        )
        project = StudentProject.objects.create(
            user=self.user, course=self.course, title="Projeto", summary="Resumo", status="published"
        )
        self.client.force_authenticate(other)
        response = self.client.patch(
            reverse("student-project-detail", kwargs={"pk": project.id}), {"title": "Alterado"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
