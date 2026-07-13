import re

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(Course, related_name='modules', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    module = models.ForeignKey(Module, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    CONTENT_TYPES = [
        ('VIDEO', 'Trilha de Vídeo'),
        ('ARTICLE', 'Apostila (PDF/Texto)'),
        ('LAB', 'Laboratório Interativo')
    ]
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES)

    file_upload = models.FileField(upload_to='lessons/files/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    body = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Exercise(models.Model):
    EXERCISE_TYPES = [
        ('SQL', 'SQL'),
        ('PYTHON', 'Python'),
        ('MULTIPLE_CHOICE', 'Múltipla escolha'),
        ('OPEN', 'Resposta aberta'),
    ]

    EVALUATION_MODES = [
        ('keywords', 'Palavras-chave'),
        ('exact', 'Texto exato'),
        ('contains', 'Contém resposta esperada'),
    ]

    lesson = models.OneToOneField(Lesson, related_name='exercise', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    statement = models.TextField(blank=True)
    answer_type = models.CharField(max_length=30, choices=EXERCISE_TYPES, default='SQL')
    expected_answer = models.TextField(blank=True)
    expected_keywords = models.JSONField(default=list, blank=True)
    evaluation_mode = models.CharField(max_length=20, choices=EVALUATION_MODES, default='keywords')
    points = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def evaluate_answer(self, answer):
        if not answer:
            return False

        normalized_answer = re.sub(r'\s+', ' ', answer.strip().lower())
        normalized_expected = re.sub(r'\s+', ' ', self.expected_answer.strip().lower())

        if self.evaluation_mode == 'exact':
            return normalized_answer == normalized_expected

        if self.evaluation_mode == 'contains':
            return normalized_expected in normalized_answer

        keywords = [k.lower() for k in self.expected_keywords if k]
        if not keywords:
            return bool(normalized_expected and normalized_expected in normalized_answer)

        return all(keyword in normalized_answer for keyword in keywords)
