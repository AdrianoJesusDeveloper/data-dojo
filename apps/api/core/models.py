import re

from django.db import models
from django.contrib.auth.models import AbstractUser


# ============================================================
# USUÁRIO
# ============================================================

class User(AbstractUser):
    """
    Usuário personalizado da plataforma Data Driven Dojô.

    O login será realizado através do e-mail.
    """

    email = models.EmailField(
        unique=True
    )

    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    # Pontos Kaizen acumulados pelo aluno
    xp_points = models.PositiveIntegerField(
        default=0
    )

    # Campo utilizado para autenticação
    USERNAME_FIELD = "email"

    # Campos solicitados além do e-mail ao criar usuário
    REQUIRED_FIELDS = [
        "username"
    ]

    def __str__(self):
        return self.email


# ============================================================
# CURSOS
# ============================================================

class Course(models.Model):
    """
    Curso da plataforma.
    """

    title = models.CharField(
        max_length=200
    )

    description = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title


# ============================================================
# MÓDULOS
# ============================================================

class Module(models.Model):
    """
    Módulo pertencente a um curso.
    """

    course = models.ForeignKey(
        Course,
        related_name="modules",
        on_delete=models.CASCADE
    )

    title = models.CharField(
        max_length=200
    )

    order = models.PositiveIntegerField(
        default=0
    )

    def __str__(self):
        return f"{self.course.title} - {self.title}"


# ============================================================
# AULAS
# ============================================================

class Lesson(models.Model):
    """
    Aula pertencente a um módulo.
    """

    CONTENT_TYPES = [
        ("VIDEO", "Trilha de Vídeo"),
        ("ARTICLE", "Apostila (PDF/Texto)"),
        ("LAB", "Laboratório Interativo"),
    ]

    module = models.ForeignKey(
        Module,
        related_name="lessons",
        on_delete=models.CASCADE
    )

    title = models.CharField(
        max_length=200
    )

    content_type = models.CharField(
        max_length=50,
        choices=CONTENT_TYPES
    )

    file_upload = models.FileField(
        upload_to="lessons/files/",
        blank=True,
        null=True
    )

    video_url = models.URLField(
        blank=True,
        null=True
    )

    body = models.TextField(
        blank=True
    )

    order = models.PositiveIntegerField(
        default=0
    )

    def __str__(self):
        return self.title


# ============================================================
# EXERCÍCIOS
# ============================================================

class Exercise(models.Model):
    """
    Exercício associado a uma aula.

    Cada aula pode possuir no máximo um exercício.
    """

    EXERCISE_TYPES = [
        ("SQL", "SQL"),
        ("PYTHON", "Python"),
        ("MULTIPLE_CHOICE", "Múltipla escolha"),
        ("OPEN", "Resposta aberta"),
    ]

    EVALUATION_MODES = [
        ("keywords", "Palavras-chave"),
        ("exact", "Texto exato"),
        ("contains", "Contém resposta esperada"),
    ]

    lesson = models.OneToOneField(
        Lesson,
        related_name="exercise",
        on_delete=models.CASCADE
    )

    title = models.CharField(
        max_length=200
    )

    statement = models.TextField(
        blank=True
    )

    answer_type = models.CharField(
        max_length=30,
        choices=EXERCISE_TYPES,
        default="SQL"
    )

    expected_answer = models.TextField(
        blank=True
    )

    expected_keywords = models.JSONField(
        default=list,
        blank=True
    )

    evaluation_mode = models.CharField(
        max_length=20,
        choices=EVALUATION_MODES,
        default="keywords"
    )

    points = models.PositiveIntegerField(
        default=100
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title

    def evaluate_answer(self, answer):
        """
        Avalia a resposta enviada pelo aluno.
        """

        if not answer:
            return False

        normalized_answer = re.sub(
            r"\s+",
            " ",
            answer.strip().lower()
        )

        normalized_expected = re.sub(
            r"\s+",
            " ",
            self.expected_answer.strip().lower()
        )

        # Avaliação por texto exato
        if self.evaluation_mode == "exact":
            return normalized_answer == normalized_expected

        # Avaliação verificando se contém a resposta esperada
        if self.evaluation_mode == "contains":
            return (
                bool(normalized_expected)
                and normalized_expected in normalized_answer
            )

        # Avaliação por palavras-chave
        keywords = [
            str(keyword).strip().lower()
            for keyword in self.expected_keywords
            if keyword
        ]

        if not keywords:
            return (
                bool(normalized_expected)
                and normalized_expected in normalized_answer
            )

        return all(
            keyword in normalized_answer
            for keyword in keywords
        )


# ============================================================
# COMUNIDADE
# ============================================================

class ForumTopic(models.Model):
    """
    Tópico criado por um aluno na Comunidade.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="forum_topics"
    )

    title = models.CharField(
        max_length=251
    )

    content = models.TextField(
        help_text="Texto explicativo da dúvida"
    )

    code_screenshot = models.ImageField(
        upload_to="forum/screenshots/",
        blank=True,
        null=True
    )

    # Usuários que curtiram o tópico
    likes = models.ManyToManyField(
        User,
        related_name="liked_forum_topics",
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username}: {self.title}"


# ============================================================
# COMENTÁRIOS DA COMUNIDADE
# ============================================================

class ForumComment(models.Model):
    """
    Comentário/resposta dentro de um tópico.
    """

    topic = models.ForeignKey(
        ForumTopic,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    content = models.TextField()

    code_screenshot = models.ImageField(
        upload_to="forum/screenshots/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Resposta de "
            f"{self.user.username} "
            f"no tópico {self.topic.id}"
        )


# ============================================================
# CERTIFICADOS
# ============================================================

class Certificate(models.Model):
    """
    Certificado conquistado por um aluno.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="certificates"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    issued_at = models.DateTimeField(
        auto_now_add=True
    )

    verification_code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Código único de validação"
    )

    def __str__(self):
        return (
            f"Certificado de "
            f"{self.user.username} - "
            f"{self.course.title}"
        )