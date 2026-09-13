import re

from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


MAX_SUBMITTED_ANSWER_LENGTH = 20_000


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

    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)

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


class Enrollment(models.Model):
    """Persistent relationship between a student and a course."""

    STATUS_ACTIVE = "active"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Ativa"),
        (STATUS_CANCELLED, "Cancelada"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="enrollments",
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(
        Course,
        related_name="enrollments",
        on_delete=models.PROTECT,
    )
    enrolled_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="unique_user_course_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.user_id}:{self.course_id} ({self.status})"


class CourseProgress(models.Model):
    """Server-owned academic progress state for one enrollment."""

    STATE_NOT_STARTED = "not_started"
    STATE_IN_PROGRESS = "in_progress"
    STATE_COMPLETED = "completed"
    ACADEMIC_STATE_CHOICES = [
        (STATE_NOT_STARTED, "Não iniciado"),
        (STATE_IN_PROGRESS, "Em andamento"),
        (STATE_COMPLETED, "Concluído"),
    ]

    enrollment = models.OneToOneField(
        Enrollment,
        related_name="progress",
        on_delete=models.CASCADE,
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    academic_state = models.CharField(
        max_length=20,
        choices=ACADEMIC_STATE_CHOICES,
        default=STATE_NOT_STARTED,
        db_index=True,
    )
    first_activity_at = models.DateTimeField(blank=True, null=True)
    last_activity_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(percentage__gte=0, percentage__lte=100),
                name="course_progress_percentage_range",
            )
        ]

    def __str__(self):
        return f"{self.enrollment_id}: {self.percentage}%"


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


class LessonProgress(models.Model):
    """Server-owned state for one lesson within one course enrollment."""

    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, "Não iniciada"),
        (STATUS_IN_PROGRESS, "Em andamento"),
        (STATUS_COMPLETED, "Concluída"),
    ]

    course_progress = models.ForeignKey(
        CourseProgress,
        related_name="lesson_progress",
        on_delete=models.CASCADE,
    )
    lesson = models.ForeignKey(
        Lesson,
        related_name="student_progress",
        on_delete=models.PROTECT,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_STARTED,
        db_index=True,
    )
    started_at = models.DateTimeField(blank=True, null=True)
    last_activity_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_activity_at", "lesson_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["course_progress", "lesson"],
                name="unique_course_progress_lesson",
            )
        ]

    def clean(self):
        super().clean()
        if (
            self.course_progress_id
            and self.lesson_id
            and self.course_progress.enrollment.course_id != self.lesson.module.course_id
        ):
            raise ValidationError("A aula deve pertencer ao curso da matrícula.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course_progress_id}:{self.lesson_id} ({self.status})"


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

        if not isinstance(answer, str) or not answer.strip():
            return False

        if self.evaluation_mode not in dict(self.EVALUATION_MODES):
            raise ValueError("Invalid exercise evaluation mode.")

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


class ExerciseAttempt(models.Model):
    """Immutable, server-evaluated answer submitted by a student."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="exercise_attempts",
        on_delete=models.CASCADE,
    )
    exercise = models.ForeignKey(
        Exercise,
        related_name="attempts",
        on_delete=models.PROTECT,
    )
    idempotency_key = models.UUIDField()
    submitted_answer = models.TextField(
        validators=[MaxLengthValidator(MAX_SUBMITTED_ANSWER_LENGTH)]
    )
    attempt_number = models.PositiveIntegerField()
    passed = models.BooleanField(default=False, db_index=True)
    feedback = models.JSONField(default=dict)
    evaluation_version = models.CharField(max_length=32, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attempt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "exercise", "attempt_number"],
                name="unique_user_exercise_attempt_number",
            ),
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                name="unique_user_attempt_idempotency_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "exercise", "-created_at"],
                name="attempt_user_exercise_date_idx",
            )
        ]

    def __str__(self):
        return f"{self.user_id}:{self.exercise_id}#{self.attempt_number}"


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

    updated_at = models.DateTimeField(
        auto_now=True
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

    likes = models.ManyToManyField(
        User,
        related_name="liked_forum_comments",
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
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


class StudentProject(models.Model):
    STATUS_CHOICES = [("draft", "Rascunho"), ("published", "Publicado")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolio_projects")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="student_projects")
    title = models.CharField(max_length=180)
    summary = models.CharField(max_length=320)
    description = models.TextField(blank=True)
    technologies = models.JSONField(default=list, blank=True)
    repository_url = models.URLField(blank=True)
    demo_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-featured", "-updated_at"]

    def __str__(self):
        return f"{self.title} — {self.user.username}"
