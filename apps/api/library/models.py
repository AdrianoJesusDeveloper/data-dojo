from django.conf import settings
from django.db import models


class LibrarySource(models.Model):
    STATUS_CHOICES = [
        ("discovered", "Descoberto"),
        ("supported", "Suportado"),
        ("unsupported", "Ainda não suportado"),
        ("missing", "Arquivo ausente"),
    ]

    relative_path = models.TextField(unique=True)
    filename = models.CharField(max_length=500)
    extension = models.CharField(max_length=20)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="discovered")
    modified_at = models.DateTimeField(null=True, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["relative_path"]

    def __str__(self):
        return self.relative_path


class Trilha(models.Model):
    nome = models.CharField(max_length=120)
    foco = models.TextField(help_text="Descrição do público/foco da trilha")
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class Book(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Enviado"),
        ("processing", "Processando"),
        ("ready", "Pronto"),
        ("error", "Erro"),
    ]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    source = models.OneToOneField(
        LibrarySource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="book",
    )
    trilha = models.ForeignKey(Trilha, on_delete=models.SET_NULL, null=True, related_name="books")
    tecnologias = models.JSONField(default=list, blank=True)
    file = models.FileField(upload_to="library/books/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    total_chunks = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class BookChunk(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    content = models.TextField()
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["book", "chunk_index"], name="unique_book_chunk")]
        indexes = [models.Index(fields=["book", "chunk_index"])]
        ordering = ["chunk_index"]


class GeneratedScript(models.Model):
    trilha = models.ForeignKey(Trilha, on_delete=models.SET_NULL, null=True, related_name="scripts")
    books = models.ManyToManyField(Book, related_name="scripts")
    titulo_video = models.CharField(max_length=255)
    problema_resolvido = models.TextField()
    ganho_negocio = models.TextField()
    estrutura = models.JSONField(default=dict)
    conteudo_bruto = models.TextField(help_text="Resposta completa gerada pela IA")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.titulo_video


class StudioProject(models.Model):
    PROJECT_TYPES = [("youtube", "Trilha YouTube"), ("premium", "Formação Premium")]
    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("planning", "Planejamento"),
        ("awaiting_approval", "Aguardando aprovação"),
        ("approved", "Aprovado"),
        ("implementing", "Em implementação"),
        ("validating", "Em validação"),
        ("content", "Produção de conteúdo"),
        ("complete", "Concluído"),
    ]

    title = models.CharField(max_length=255)
    theme = models.CharField(max_length=500)
    objective = models.TextField()
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES, default="premium")
    source = models.ForeignKey(LibrarySource, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    books = models.ManyToManyField(Book, blank=True, related_name="studio_projects")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="studio_projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class ModernizationPlan(models.Model):
    STATUS_CHOICES = [("draft", "Rascunho"), ("review", "Em revisão"), ("approved", "Aprovado")]
    project = models.OneToOneField(StudioProject, on_delete=models.CASCADE, related_name="modernization_plan")
    source_summary = models.TextField(blank=True)
    original_architecture = models.JSONField(default=dict)
    proposed_architecture = models.JSONField(default=dict)
    replacements = models.JSONField(default=list)
    requirements = models.JSONField(default=dict)
    acceptance_criteria = models.JSONField(default=list)
    test_strategy = models.JSONField(default=dict)
    risks = models.JSONField(default=list)
    business_value = models.TextField(blank=True)
    raw_response = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EditorialPlanVersion(models.Model):
    ORIGIN_CHOICES = [("ai", "IA"), ("human_edit", "EdiÃ§Ã£o humana"), ("revision", "RevisÃ£o")]
    project = models.ForeignKey(StudioProject, on_delete=models.CASCADE, related_name="plan_versions")
    version = models.PositiveIntegerField()
    content = models.JSONField(default=dict)
    project_type = models.CharField(max_length=20, choices=StudioProject.PROJECT_TYPES)
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES)
    state = models.CharField(max_length=20, choices=ModernizationPlan.STATUS_CHOICES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["project", "version"], name="unique_project_plan_version")]


class EditorialComment(models.Model):
    TARGET_CHOICES = [(value, value.title()) for value in ("plan", "module", "lesson", "video", "project", "section")]
    project = models.ForeignKey(StudioProject, on_delete=models.CASCADE, related_name="editorial_comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField()
    target = models.CharField(max_length=255, default="plan")
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, default="plan")
    target_id = models.CharField(max_length=255, blank=True)
    plan_version = models.PositiveIntegerField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["resolved", "-created_at"]


class SourceCitation(models.Model):
    project = models.ForeignKey(StudioProject, on_delete=models.CASCADE, related_name="citations")
    chunk = models.ForeignKey(BookChunk, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.ForeignKey(LibrarySource, on_delete=models.SET_NULL, null=True, blank=True)
    book_title = models.CharField(max_length=255, blank=True)
    page_number = models.PositiveIntegerField(null=True, blank=True)
    excerpt = models.TextField()
    purpose = models.CharField(max_length=120, default="modernization_plan")
    created_at = models.DateTimeField(auto_now_add=True)


class StudioApproval(models.Model):
    DECISIONS = [("approved", "Aprovado"), ("revision", "Solicitar revisão")]
    project = models.ForeignKey(StudioProject, on_delete=models.CASCADE, related_name="approvals")
    artifact = models.CharField(max_length=80, default="modernization_plan")
    decision = models.CharField(max_length=20, choices=DECISIONS)
    notes = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ContentPackage(models.Model):
    project = models.OneToOneField(StudioProject, on_delete=models.CASCADE, related_name="content_package")
    study_plan = models.JSONField(default=dict)
    lesson = models.JSONField(default=dict)
    kata = models.JSONField(default=dict)
    video_script = models.JSONField(default=dict)
    article = models.TextField(blank=True)
    linkedin_post = models.TextField(blank=True)
    raw_response = models.TextField(blank=True)
    generated_items = models.JSONField(default=list, blank=True)
    publication_status = models.CharField(max_length=20, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
