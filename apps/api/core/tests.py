from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Course, Exercise, Lesson, Module, StudentProject


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
