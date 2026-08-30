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
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    MAX_SUBMITTED_ANSWER_LENGTH,
    Course,
    Exercise,
    ExerciseAttempt,
    Lesson,
    Module,
    StudentProject,
)
from core.services import create_exercise_attempt


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
        course = Course.objects.create(title="Tentativas", description="Teste")
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
        self.url = reverse(
            "exercise-attempt-list", kwargs={"exercise_id": self.exercise.id}
        )

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
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attempt = ExerciseAttempt.objects.get()
        self.assertEqual(attempt.user, self.user)
        self.assertFalse(attempt.passed)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.evaluation_version, "v1")

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
