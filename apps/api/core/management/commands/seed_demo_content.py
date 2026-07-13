from django.core.management.base import BaseCommand
from core.models import Course, Module, Lesson, Exercise


class Command(BaseCommand):
    help = "Cria um curso, módulo, aula e exercício de exemplo para o ambiente de desenvolvimento"

    def handle(self, *args, **options):
        course, created = Course.objects.get_or_create(
            title="SQL para Ciência de Dados",
            defaults={"description": "Curso introdutório com vídeos, aulas e exercícios práticos de SQL."},
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Curso criado: {course.title}"))
        else:
            self.stdout.write(self.style.WARNING(f"Curso já existe: {course.title}"))

        module, created_module = Module.objects.get_or_create(
            course=course,
            title="Fundamentos do SQL",
            defaults={"order": 1},
        )

        if created_module:
            self.stdout.write(self.style.SUCCESS(f"Módulo criado: {module.title}"))
        else:
            self.stdout.write(self.style.WARNING(f"Módulo já existe: {module.title}"))

        lesson, created_lesson = Lesson.objects.get_or_create(
            module=module,
            title="Exercício 1: selecionar nomes de clientes",
            defaults={
                "content_type": "LAB",
                "body": "Escreva uma consulta SQL que retorne os nomes dos clientes.",
                "order": 1,
            },
        )

        if created_lesson:
            self.stdout.write(self.style.SUCCESS(f"Aula criada: {lesson.title}"))
        else:
            self.stdout.write(self.style.WARNING(f"Aula já existe: {lesson.title}"))

        exercise, created_exercise = Exercise.objects.get_or_create(
            lesson=lesson,
            defaults={
                "title": "Exercício 1: selecionar nomes de clientes",
                "statement": "Escreva uma consulta SQL que retorne os nomes dos clientes da tabela clientes.",
                "answer_type": "SQL",
                "expected_answer": "SELECT name FROM customers",
                "expected_keywords": ["SELECT", "FROM"],
                "evaluation_mode": "keywords",
                "points": 100,
            },
        )

        if created_exercise:
            self.stdout.write(self.style.SUCCESS(f"Exercício criado: {exercise.title}"))
        else:
            self.stdout.write(self.style.WARNING(f"Exercício já existe: {exercise.title}"))
