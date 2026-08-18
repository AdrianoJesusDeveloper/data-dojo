from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Course, Exercise, Lesson, Module


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
