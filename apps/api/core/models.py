import re

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # Campo para armazenar a foto de perfil do aluno
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    # Total de Pontos Kaizen acumulados
    xp_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username


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


# =====================================================================
# NOVOS MODELOS ADICIONADOS: COMUNIDADE E CERTIFICADOS
# =====================================================================

class ForumTopic(models.Model):
    """Modelo para as perguntas enviadas pelos alunos na Comunidade"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_topics')
    title = models.CharField(max_length=250)
    content = models.TextField(help_text="Texto explicativo da dúvida")
    # Campo para permitir upload de fotos de erro ou prints de códigos
    code_screenshot = models.ImageField(upload_to='forum/screenshots/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.title}"


class ForumComment(models.Model):
    """Modelo para as respostas dadas nos tópicos do fórum"""
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    # Permite imagem também nas respostas
    code_screenshot = models.ImageField(upload_to='forum/screenshots/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resposta de {self.user.username} no tópico {self.topic.id}"


class Certificate(models.Model):
    """Modelo para registrar os certificados que os alunos conquistarem"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    issued_at = models.DateTimeField(auto_now_add=True)
    verification_code = models.CharField(max_length=100, unique=True, help_text="Código único de validação")

    def __str__(self):
        return f"Certificado de {self.user.username} - {self.course.title}"