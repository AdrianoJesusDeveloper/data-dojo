from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
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
    progress_percent = models.PositiveSmallIntegerField(default=0)
    progress_stage = models.CharField(max_length=40, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    duplicate_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="duplicates")
    lifecycle = models.CharField(max_length=12, default="active", choices=[("active", "Ativo"), ("archived", "Arquivado"), ("discarded", "Descartado")], db_index=True)
    category = models.CharField(max_length=100, blank=True)
    is_favorite = models.BooleanField(default=False)
    cover_asset = models.ForeignKey("MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="covered_books")
    error_code = models.CharField(max_length=40, blank=True)
    error_stage = models.CharField(max_length=80, blank=True)
    technical_error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["sha256"], condition=~models.Q(sha256="") & models.Q(duplicate_of__isnull=True), name="unique_original_book_hash")]

    def __str__(self):
        return self.title


class MediaAsset(models.Model):
    CATEGORIES = [(value, value) for value in ("BOOK_COVER", "BOOK_THUMBNAIL", "LOGO", "BACKGROUND", "OTHER")]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="library/assets/")
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=80)
    file_size = models.PositiveBigIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="OTHER")
    source_type = models.CharField(max_length=20, default="upload")
    source_url = models.URLField(blank=True)
    author = models.CharField(max_length=255, blank=True)
    license = models.CharField(max_length=255, blank=True)
    is_favorite = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BookSection(models.Model):
    """Original extracted text, also used for OCR search; chunks remain the RAG index."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="sections")
    position = models.PositiveIntegerField()
    location = models.CharField(max_length=500)
    title = models.CharField(max_length=500, blank=True)
    text = models.TextField()
    html = models.TextField(blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [models.UniqueConstraint(fields=["book", "position"], name="unique_book_section")]


class ReadingProgress(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reading_progress")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    location = models.CharField(max_length=500, blank=True)
    position = models.PositiveIntegerField(default=1)
    offset = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1)])
    progress_percentage = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["book", "user"], name="unique_book_user_progress")]


class ReadingMark(models.Model):
    """One location contract shared by bookmarks, annotations and text highlights."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reading_marks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12, choices=[("bookmark", "Marcador"), ("annotation", "Anotação"), ("highlight", "Destaque")])
    location = models.CharField(max_length=500)
    position = models.PositiveIntegerField(default=1)
    offset = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1)])
    selected_text = models.TextField(blank=True)
    start_offset = models.PositiveIntegerField(null=True, blank=True)
    end_offset = models.PositiveIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "id"]


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
    PROJECT_TYPES = [("content", "Conteúdo Editorial"), ("formation", "Formação Premium")]

    # Fundação multiformato: project_type continua representando o fluxo editorial
    # legado (YouTube/Premium), enquanto canal e formato descrevem a saída desejada.
    # Os campos aceitam vazio para preservar projetos existentes e permitir migração
    # incremental sem criar silos paralelos.
    PRODUCTION_CHANNELS = [
        ("youtube", "YouTube"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
        ("premium", "Formação Premium"),
    ]
    PRODUCTION_FORMATS = [
        ("long_video", "Vídeo completo"),
        ("short_vertical", "Short / vídeo vertical curto"),
        ("reel", "Reel"),
        ("feed_post", "Post de feed"),
        ("carousel", "Carrossel"),
        ("stories", "Stories"),
        ("article", "Artigo"),
        ("premium_formation", "Formação Premium"),
        ("premium_lesson", "Aula Premium"),
        ("slides", "Slides"),
        ("recording_package", "Pacote de gravação"),
    ]

    RESEARCH_POLICIES = [
        ("ACERVO_ONLY", "Somente acervo"),
        ("WEB_ONLY", "Somente web"),
        ("HYBRID", "Acervo e web"),
    ]
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
    original_intent = models.TextField(blank=True)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES, default="formation")
    production_channel = models.CharField(
        max_length=20,
        choices=PRODUCTION_CHANNELS,
        blank=True,
        default="",
        db_index=True,
        help_text="Canal principal da produção multiformato. Vazio preserva projetos editoriais legados.",
    )
    production_format = models.CharField(
        max_length=30,
        choices=PRODUCTION_FORMATS,
        blank=True,
        default="",
        db_index=True,
        help_text="Formato principal desejado. Artefatos derivados continuam registrados em StudioArtifact.",
    )
    research_policy = models.CharField(max_length=20, choices=RESEARCH_POLICIES, default="ACERVO_ONLY")
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

    @property
    def is_content_flow(self) -> bool:
        """
        Camada de compatibilidade semântica.

        Enquanto os dados legados ainda usam "youtube"/"premium", o domínio
        novo passa a enxergar os fluxos como "content"/"formation".
        """
        return self.project_type in {"youtube", "content"}

    @property
    def is_formation_flow(self) -> bool:
        """
        Camada de compatibilidade semântica para o fluxo de formação.
        """
        return self.project_type in {"premium", "formation"}

    @property
    def semantic_project_type(self) -> str:
        """
        Nome semântico estável usado na migração gradual do domínio.
        """
        if self.is_content_flow:
            return "content"
        if self.is_formation_flow:
            return "formation"
        return self.project_type

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


class StudioResearchContext(models.Model):
    STATUS_CHOICES = [("draft", "Rascunho"), ("ready", "Pronto"), ("gap", "Lacuna"), ("failed", "Falhou")]
    project = models.OneToOneField(StudioProject, on_delete=models.CASCADE, related_name="research_context")
    policy = models.CharField(max_length=20, choices=StudioProject.RESEARCH_POLICIES)
    query = models.TextField()
    dossier = models.JSONField(default=dict, blank=True)
    conflicts = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    built_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StudioResearchEvidence(models.Model):
    SOURCE_KINDS = [("ACERVO", "Acervo"), ("WEB", "Web"), ("GAP", "Lacuna")]
    context = models.ForeignKey(StudioResearchContext, on_delete=models.CASCADE, related_name="evidence")
    source_kind = models.CharField(max_length=20, choices=SOURCE_KINDS, db_index=True)
    chunk = models.ForeignKey(BookChunk, null=True, blank=True, on_delete=models.SET_NULL, related_name="studio_research_evidence")
    url = models.URLField(max_length=2000, blank=True)
    title = models.CharField(max_length=500, blank=True)
    domain = models.CharField(max_length=255, blank=True)
    source_type = models.CharField(max_length=80, blank=True)
    query = models.TextField()
    excerpt = models.TextField(blank=True)
    retrieved_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source_kind", "id"]


class DossierVersionQuerySet(models.QuerySet):
    """Disallow ORM shortcuts that bypass version and human-review invariants."""

    def update(self, **kwargs):
        raise ValidationError("Use uma nova versão ou a transição explícita do Dossiê.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Versões do Dossiê não permitem alteração em lote.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Crie versões do Dossiê individualmente com validação.")

    def delete(self):
        raise ValidationError("O histórico do Dossiê não pode ser excluído.")


class StudioDossierVersion(models.Model):
    """Immutable content revisions; only forward human-review transitions mutate."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        REVIEW = "REVIEW", "Em revisão"
        APPROVED = "APPROVED", "Aprovado"

    class Origin(models.TextChoices):
        HUMAN_EDIT = "human_edit", "Edição humana"
        RESEARCH_SNAPSHOT = "research_snapshot", "Consolidação de pesquisa"

    project = models.ForeignKey(StudioProject, on_delete=models.PROTECT, related_name="dossier_versions")
    version = models.PositiveIntegerField()
    based_on = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="revisions")
    content = models.JSONField(default=dict, blank=True)
    schema_version = models.CharField(max_length=40, default="master-dossier-v1")
    research_policy = models.CharField(max_length=20, choices=StudioProject.RESEARCH_POLICIES)
    references_snapshot = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    origin = models.CharField(max_length=30, choices=Origin.choices, default=Origin.HUMAN_EDIT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_dossier_versions")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_dossier_versions")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    objects = DossierVersionQuerySet.as_manager()

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["project", "version"], name="unique_project_dossier_version"),
            models.CheckConstraint(condition=models.Q(version__gte=1), name="dossier_version_positive"),
            models.CheckConstraint(
                condition=(models.Q(status="APPROVED", reviewed_by__isnull=False, reviewed_at__isnull=False)
                           | models.Q(status__in=["DRAFT", "REVIEW"], reviewed_by__isnull=True, reviewed_at__isnull=True)),
                name="dossier_human_approval_required",
            ),
        ]

    def clean(self):
        from core.permissions import is_administrative_user
        from .dossier_contracts import validate_dossier

        super().clean()
        validate_dossier(self.content, self.references_snapshot, self.research_policy, self.schema_version)
        if self.based_on_id and (self.based_on.project_id != self.project_id or self.based_on.version >= self.version):
            raise ValidationError("A versão base deve ser anterior e pertencer ao mesmo projeto.")
        if self.project_id and self.created_by_id:
            if self.created_by_id != self.project.created_by_id or not self.created_by.is_active or not is_administrative_user(self.created_by):
                raise ValidationError("Somente o proprietário administrativo pode criar o Dossiê.")
        if self.reviewed_by_id:
            if self.reviewed_by_id != self.project.created_by_id or not self.reviewed_by.is_active or not is_administrative_user(self.reviewed_by):
                raise ValidationError("A aprovação exige o proprietário administrativo do projeto.")

    def save(self, *args, **kwargs):
        from django.db import router, transaction
        from .services.studio_dossier import validate_reference_origins

        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            project = StudioProject.objects.using(using).select_for_update().get(pk=self.project_id)
            previous = type(self).objects.using(using).filter(pk=self.pk).first() if self.pk else None
            if previous:
                mutable = {"status", "reviewed_by", "reviewed_at"}
                for field in self._meta.concrete_fields:
                    if field.name not in mutable and getattr(previous, field.attname) != getattr(self, field.attname):
                        raise ValidationError("Conteúdo e proveniência são imutáveis; crie uma nova versão.")
                allowed = {"DRAFT": "REVIEW", "REVIEW": "APPROVED"}
                changed = any(getattr(previous, key) != getattr(self, key) for key in ("status", "reviewed_by_id", "reviewed_at"))
                if changed and allowed.get(previous.status) != self.status:
                    raise ValidationError("Transição de revisão inválida; revisões de conteúdo exigem nova versão.")
                if changed and type(self).objects.using(using).filter(project_id=self.project_id, version__gt=self.version).exists():
                    raise ValidationError("Existe uma versão mais recente do Dossiê.")
            else:
                latest = type(self).objects.using(using).filter(project_id=self.project_id).first()
                if self.version != (latest.version + 1 if latest else 1) or self.based_on_id != (latest.pk if latest else None):
                    raise ValidationError("Versão base desatualizada; recarregue o Dossiê.")
                if self.status != self.Status.DRAFT or self.reviewed_by_id or self.reviewed_at:
                    raise ValidationError("Uma nova versão deve começar em DRAFT, sem aprovação.")
                if self.research_policy != project.research_policy:
                    raise ValidationError("A nova versão deve preservar a política atual do projeto.")
            self.full_clean()
            if previous is None:
                validate_reference_origins(self.project_id, self.references_snapshot, self.based_on)
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("O histórico do Dossiê não pode ser excluído.")


class StudioArtifact(models.Model):
    STATUS_CHOICES = [("DRAFT", "Rascunho"), ("REVIEW", "Em revisão"), ("APPROVED", "Aprovado")]
    project = models.ForeignKey(StudioProject, on_delete=models.CASCADE, related_name="artifacts")
    artifact_type = models.CharField(max_length=40)
    target_type = models.CharField(max_length=20)
    target_id = models.CharField(max_length=255)
    plan_version = models.PositiveIntegerField()
    generation = models.PositiveIntegerField(default=1)
    content = models.JSONField(default=dict)
    linked_unit = models.ForeignKey("SenseiStudyUnit", null=True, blank=True, on_delete=models.SET_NULL, related_name="studio_artifacts")
    linked_formation = models.ForeignKey("SenseiFormation", null=True, blank=True, on_delete=models.SET_NULL, related_name="studio_artifacts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT", db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="studio_artifacts")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_studio_artifacts")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["project", "target_id", "plan_version", "generation"], name="unique_studio_artifact_generation")]


class StudioFormationLink(models.Model):
    project = models.OneToOneField(StudioProject, on_delete=models.CASCADE, related_name="formation_link")
    formation = models.OneToOneField("SenseiFormation", on_delete=models.PROTECT, related_name="studio_link")
    synced_plan_version = models.PositiveIntegerField(default=0)
    identity_map = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EditorialCouncilRun(models.Model):
    STATUS_CHOICES = [(value, value.replace("_", " ").title()) for value in (
        "draft", "queued", "running", "reviewing", "awaiting_human_approval",
        "approved", "revision_requested", "failed", "cancelled",
    )]
    project = models.ForeignKey(StudioProject, on_delete=models.CASCADE, related_name="council_runs")
    plan_version = models.PositiveIntegerField()
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="draft", db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    input_snapshot = models.JSONField(default=dict)
    final_synthesis = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["project", "status", "lease_expires_at"], name="council_active_lease_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(status__in=("queued", "running", "reviewing")),
                name="unique_active_council_per_project",
            ),
        ]


class EditorialAgentRun(models.Model):
    ROLE_CHOICES = [(value, value.replace("_", " ").title()) for value in (
        "technical", "pedagogy", "learning_science", "technical_content",
        "youtube", "social_media", "seo", "fact_checker",
    )]
    STATUS_CHOICES = [(value, value.title()) for value in ("pending", "running", "completed", "failed", "skipped")]
    council_run = models.ForeignKey(EditorialCouncilRun, on_delete=models.CASCADE, related_name="agent_runs")
    role = models.CharField(max_length=40, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    provider = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=120, blank=True)
    input_payload = models.JSONField(default=dict)
    output_payload = models.JSONField(default=dict, blank=True)
    rag_sources = models.JSONField(default=list, blank=True)
    prompt_version = models.CharField(max_length=40, default="editorial-council-v1")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["council_run", "role"], name="unique_council_role")]


class SenseiFormation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        ACTIVE = "ACTIVE", "Ativa"
        PAUSED = "PAUSED", "Pausada"
        COMPLETED = "COMPLETED", "Concluída"
        ARCHIVED = "ARCHIVED", "Arquivada"

    class SourcePolicy(models.TextChoices):
        REQUIRE_APPROVED_SOURCE = "REQUIRE_APPROVED_SOURCE", "Exigir fonte aprovada"
        ALLOW_AI_WITHOUT_SOURCE = "ALLOW_AI_WITHOUT_SOURCE", "Permitir IA sem fonte aprovada"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    objective = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    source_policy = models.CharField(
        max_length=40,
        choices=SourcePolicy.choices,
        default=SourcePolicy.REQUIRE_APPROVED_SOURCE,
        db_index=True,
        help_text="Define se o Motor Didático exige fonte aprovada ou pode gerar rascunho assistido por IA sem fonte.",
    )
    level = models.CharField(max_length=80, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="sensei_formations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    workspace_course = models.OneToOneField("core.Course", null=True, blank=True, on_delete=models.SET_NULL, related_name="sensei_formation")

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class SenseiFormationModule(models.Model):
    formation = models.ForeignKey(SenseiFormation, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    workspace_module = models.OneToOneField("core.Module", null=True, blank=True, on_delete=models.SET_NULL, related_name="sensei_module")

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["formation", "order"], name="unique_sensei_module_order")]

    def __str__(self):
        return f"{self.formation.title} - {self.title}"


class SenseiStudyUnit(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        ACTIVE = "ACTIVE", "Ativa"
        ARCHIVED = "ARCHIVED", "Arquivada"

    module = models.ForeignKey(SenseiFormationModule, on_delete=models.CASCADE, related_name="study_units")
    title = models.CharField(max_length=255)
    objective = models.TextField()
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    sources = models.ManyToManyField(LibrarySource, blank=True, related_name="sensei_study_units")
    reference_links = models.JSONField(default=list, blank=True, help_text="Referências tipadas futuras que ainda não pertencem ao acervo local.")

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["module", "order"], name="unique_sensei_unit_order")]

    def __str__(self):
        return self.title


class SenseiCompetency(models.Model):
    class MasteryLevel(models.IntegerChoices):
        KNOWS = 1, "Conhece"
        EXPLAINS = 2, "Explica"
        IMPLEMENTS = 3, "Implementa"
        DEBUGS = 4, "Debuga"
        JUSTIFIES = 5, "Justifica decisões"
        TEACHES = 6, "Ensina"

    formation = models.ForeignKey(SenseiFormation, on_delete=models.CASCADE, related_name="competencies")
    module = models.ForeignKey(SenseiFormationModule, null=True, blank=True, on_delete=models.CASCADE, related_name="competencies")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    expected_level = models.PositiveSmallIntegerField(choices=MasteryLevel.choices, default=MasteryLevel.TEACHES)
    mastery_criteria = models.JSONField(default=list)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def clean(self):
        super().clean()
        if self.module_id and self.module.formation_id != self.formation_id:
            raise ValidationError({"module": "O módulo deve pertencer à mesma formação da competência."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SenseiLearningActivity(models.Model):
    """Pedagogical practice record; it is never validated mastery evidence."""

    class ActivityType(models.TextChoices):
        CONCEPTUAL_QUESTION = "CONCEPTUAL_QUESTION", "Pergunta conceitual"
        OWN_WORDS = "OWN_WORDS", "Explicação com palavras próprias"
        IMPLEMENTATION = "IMPLEMENTATION", "Exercício de implementação"
        DEBUGGING = "DEBUGGING", "Debugging"
        SOLUTION_COMPARISON = "SOLUTION_COMPARISON", "Comparação entre soluções"
        DECISION_JUSTIFICATION = "DECISION_JUSTIFICATION", "Justificativa de decisão"
        PRACTICAL_CHALLENGE = "PRACTICAL_CHALLENGE", "Pequeno desafio prático"
        TECHNICAL_DEFENSE = "TECHNICAL_DEFENSE", "Pergunta de defesa técnica"

    class State(models.TextChoices):
        GENERATED = "GENERATED", "Gerada"
        ANSWERED = "ANSWERED", "Respondida"
        REVIEWED = "REVIEWED", "Revisada"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_learning_activities")
    unit = models.ForeignKey(SenseiStudyUnit, on_delete=models.CASCADE, related_name="learning_activities")
    competency = models.ForeignKey(SenseiCompetency, on_delete=models.PROTECT, related_name="learning_activities")
    ai_provider = models.CharField(max_length=40, blank=True, default="")
    ai_model = models.CharField(max_length=120, blank=True, default="")
    activity_type = models.CharField(max_length=40, choices=ActivityType.choices)
    prompt = models.TextField()
    difficulty_level = models.PositiveSmallIntegerField(choices=SenseiCompetency.MasteryLevel.choices)
    pedagogical_context = models.JSONField(default=dict)
    learner_response = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    feedback_metadata = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.GENERATED, db_index=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "unit", "state"], name="sensei_activity_lookup")]

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.unit}"


class SenseiLearningAttempt(models.Model):
    """Append-only attempt and feedback history for one learning activity."""

    activity = models.ForeignKey(SenseiLearningActivity, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_learning_attempts")
    ai_provider = models.CharField(max_length=40, blank=True, default="")
    ai_model = models.CharField(max_length=120, blank=True, default="")
    attempt_number = models.PositiveIntegerField()
    answer = models.TextField()
    feedback = models.TextField()
    outcome = models.CharField(max_length=30)
    identified_gap = models.TextField(blank=True)
    next_step = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["attempt_number", "id"]
        constraints = [
            models.UniqueConstraint(fields=["activity", "attempt_number"], name="unique_sensei_activity_attempt"),
        ]

    def __str__(self):
        return f"Atividade {self.activity_id} - tentativa {self.attempt_number}"


class SenseiLearningProviderPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_learning_provider_preferences")
    formation = models.ForeignKey(SenseiFormation, on_delete=models.CASCADE, related_name="learning_provider_preferences")
    provider = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "formation"], name="unique_sensei_provider_preference"),
        ]


class SenseiCompetencyEvidence(models.Model):
    class EvidenceType(models.TextChoices):
        WRITTEN_EXPLANATION = "WRITTEN_EXPLANATION", "Explicação escrita"
        EXERCISE = "EXERCISE", "Exercício"
        CODE = "CODE", "Código"
        PROJECT = "PROJECT", "Projeto"
        ARCHITECTURE = "ARCHITECTURE", "Arquitetura"
        TECHNICAL_DECISION = "TECHNICAL_DECISION", "Decisão técnica"
        DEBUGGING = "DEBUGGING", "Debugging"
        PRESENTATION = "PRESENTATION", "Apresentação"
        TAUGHT_CLASS = "TAUGHT_CLASS", "Aula ministrada"
        ORAL_ASSESSMENT = "ORAL_ASSESSMENT", "Avaliação oral"

    class ValidationStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        VALIDATED = "VALIDATED", "Validada"
        REJECTED = "REJECTED", "Rejeitada"

    competency = models.ForeignKey(SenseiCompetency, on_delete=models.CASCADE, related_name="evidences")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sensei_evidences")
    evidence_type = models.CharField(max_length=40, choices=EvidenceType.choices)
    description = models.TextField()
    content = models.TextField(blank=True)
    reference_url = models.URLField(blank=True)
    demonstrated_level = models.PositiveSmallIntegerField(choices=SenseiCompetency.MasteryLevel.choices)
    validation_status = models.CharField(max_length=20, choices=ValidationStatus.choices, default=ValidationStatus.PENDING, db_index=True)
    feedback = models.TextField(blank=True)
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="validated_sensei_evidences")
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class SenseiProgress(models.Model):
    class State(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Não iniciada"
        IN_PROGRESS = "IN_PROGRESS", "Em andamento"
        COMPLETED = "COMPLETED", "Concluída"

    formation = models.ForeignKey(SenseiFormation, on_delete=models.CASCADE, related_name="progress_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_progress")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    state = models.CharField(max_length=20, choices=State.choices, default=State.NOT_STARTED, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["formation", "user"], name="unique_sensei_formation_progress"),
            models.CheckConstraint(condition=models.Q(percentage__gte=0, percentage__lte=100), name="sensei_progress_percentage_range"),
        ]


class SenseiCompetencyProgress(models.Model):
    class State(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Não iniciada"
        STUDYING = "STUDYING", "Estudando"
        PRACTICING = "PRACTICING", "Praticando"
        DEMONSTRATED = "DEMONSTRATED", "Demonstrada"
        TEACHING_READY = "TEACHING_READY", "Apto para ensinar"

    competency = models.ForeignKey(SenseiCompetency, on_delete=models.CASCADE, related_name="progress_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_competency_progress")
    current_level = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(6)])
    state = models.CharField(max_length=20, choices=State.choices, default=State.NOT_STARTED, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["competency", "user"], name="unique_sensei_competency_progress"),
            models.CheckConstraint(condition=models.Q(current_level__gte=0, current_level__lte=6), name="sensei_competency_level_range"),
        ]


class SenseiUnitSource(models.Model):
    class EditorialStatus(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposta"
        APPROVED = "APPROVED", "Aprovada"
        REJECTED = "REJECTED", "Rejeitada"

    class Category(models.TextChoices):
        PRIMARY = "PRIMARY", "Primária"
        FOUNDATIONAL = "FOUNDATIONAL", "Fundacional"
        INDUSTRY = "INDUSTRY", "Indústria"
        SUPPLEMENTARY = "SUPPLEMENTARY", "Complementar"
        SENSEI = "SENSEI", "Sensei"

    class SourceType(models.TextChoices):
        OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION", "Documentação oficial"
        SPECIFICATION = "SPECIFICATION", "Especificação"
        PAPER = "PAPER", "Paper"
        OFFICIAL_REPOSITORY = "OFFICIAL_REPOSITORY", "Repositório oficial"
        ACADEMIC_BOOK = "ACADEMIC_BOOK", "Livro acadêmico"
        TECHNICAL_BOOK = "TECHNICAL_BOOK", "Livro técnico"
        UNIVERSITY_MATERIAL = "UNIVERSITY_MATERIAL", "Material universitário"
        ENGINEERING_BLOG = "ENGINEERING_BLOG", "Blog de engenharia"
        TECHNICAL_CASE = "TECHNICAL_CASE", "Caso técnico"
        TECHNICAL_CONFERENCE = "TECHNICAL_CONFERENCE", "Conferência técnica"
        COURSE = "COURSE", "Curso"
        VIDEO = "VIDEO", "Vídeo ou transcrição"
        TUTORIAL = "TUTORIAL", "Tutorial"
        ARTICLE = "ARTICLE", "Artigo técnico"
        CODE = "CODE", "Código"
        DATASET = "DATASET", "Dataset"
        NOTEBOOK = "NOTEBOOK", "Notebook"
        NOTE = "NOTE", "Anotação"
        REAL_PROJECT = "REAL_PROJECT", "Projeto real"
        ARCHITECTURAL_DECISION = "ARCHITECTURAL_DECISION", "Decisão arquitetural"
        WEB_RESEARCH = "WEB_RESEARCH", "Pesquisa web"

    unit = models.ForeignKey(SenseiStudyUnit, on_delete=models.CASCADE, related_name="curated_sources")
    source = models.ForeignKey(LibrarySource, null=True, blank=True, on_delete=models.PROTECT, related_name="sensei_unit_links")
    category = models.CharField(max_length=20, choices=Category.choices)
    source_type = models.CharField(max_length=40, choices=SourceType.choices)
    title = models.CharField(max_length=500)
    reference = models.TextField(blank=True)
    location = models.CharField(max_length=500, blank=True, help_text="Capítulo, seção, páginas ou trecho a estudar.")
    objective = models.TextField()
    priority = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    notes = models.TextField(blank=True)
    is_required = models.BooleanField(default=False)
    url = models.URLField(blank=True)
    author_or_organization = models.CharField(max_length=500, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    accessed_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    justification = models.TextField(blank=True)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    reliability_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    editorial_status = models.CharField(max_length=20, choices=EditorialStatus.choices, default=EditorialStatus.PROPOSED, db_index=True)
    curated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="curated_sensei_sources")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_sensei_sources")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "id"]
        constraints = [models.UniqueConstraint(fields=["unit", "source"], condition=models.Q(source__isnull=False), name="unique_sensei_unit_library_source")]


class SenseiUnitSourceGap(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Fonte necessária"
        RESOLVED = "RESOLVED", "Resolvida"

    unit = models.OneToOneField(SenseiStudyUnit, on_delete=models.CASCADE, related_name="source_gap")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    reason = models.TextField()
    requirements = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="sensei_source_gaps")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="resolved_sensei_source_gaps")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DidacticLesson(models.Model):
    class Audience(models.TextChoices):
        SENSEI = "SENSEI", "Sensei"
        STUDENT = "STUDENT", "Aluno"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        REVIEW = "REVIEW", "Em revisão"
        APPROVED = "APPROVED", "Aprovada"
        PUBLISHED = "PUBLISHED", "Publicada"
        ARCHIVED = "ARCHIVED", "Arquivada"

    class SourceMode(models.TextChoices):
        APPROVED_SOURCES = "APPROVED_SOURCES", "Fontes aprovadas"
        AI_GENERATED_UNSOURCED = "AI_GENERATED_UNSOURCED", "Gerada por IA sem fonte aprovada"

    title = models.CharField(max_length=255)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.SENSEI)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    source_mode = models.CharField(
        max_length=40,
        choices=SourceMode.choices,
        default=SourceMode.APPROVED_SOURCES,
        db_index=True,
        help_text="Registra se a aula foi fundamentada em fontes aprovadas ou gerada por IA sem fonte aprovada.",
    )
    learning_target_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="didactic_lessons")
    learning_target_id = models.PositiveBigIntegerField()
    learning_target = GenericForeignKey("learning_target_type", "learning_target_id")
    ai_provider = models.CharField(max_length=40, blank=True, default="")
    ai_model = models.CharField(max_length=120, blank=True, default="")
    generated_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="authored_didactic_lessons")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_didactic_lessons")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sources = models.ManyToManyField(SenseiUnitSource, blank=True, related_name="didactic_lessons")
    origin_lesson = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="student_derivation")
    origin_updated_at = models.DateTimeField(null=True, blank=True)
    workspace_lesson = models.OneToOneField("core.Lesson", null=True, blank=True, on_delete=models.SET_NULL, related_name="didactic_student_lesson")

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["learning_target_type", "learning_target_id", "audience"], name="unique_didactic_lesson_target_audience")]


class DidacticLessonSection(models.Model):
    class SectionType(models.TextChoices):
        LEARNING_OBJECTIVES = "LEARNING_OBJECTIVES", "Objetivos de aprendizagem"
        WHY_IT_MATTERS = "WHY_IT_MATTERS", "Por que importa"
        PREREQUISITES = "PREREQUISITES", "Pré-requisitos"
        CONCEPT = "CONCEPT", "Conceito"
        FOUNDATION = "FOUNDATION", "Fundamento"
        EXAMPLE = "EXAMPLE", "Exemplo"
        DEMONSTRATION = "DEMONSTRATION", "Demonstração"
        CASE_STUDY = "CASE_STUDY", "Estudo de caso"
        COMMON_MISTAKES = "COMMON_MISTAKES", "Erros comuns"
        AI_USAGE = "AI_USAGE", "Uso de IA"
        GUIDED_PRACTICE = "GUIDED_PRACTICE", "Prática guiada"
        EXERCISE = "EXERCISE", "Exercício"
        AUTHORSHIP_CHALLENGE = "AUTHORSHIP_CHALLENGE", "Desafio de autoria"
        PROJECT = "PROJECT", "Projeto"
        REFLECTION = "REFLECTION", "Reflexão"
        SELF_ASSESSMENT = "SELF_ASSESSMENT", "Autoavaliação"
        MASTERY_CRITERIA = "MASTERY_CRITERIA", "Critérios de domínio"
        REFERENCES = "REFERENCES", "Referências"

    lesson = models.ForeignKey(DidacticLesson, on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(max_length=40, choices=SectionType.choices)
    title = models.CharField(max_length=255)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["lesson", "order"], name="unique_didactic_lesson_section_order")]


class DidacticPublication(models.Model):
    class Scope(models.TextChoices):
        LESSON = "LESSON", "Aula"
        MODULE = "MODULE", "Módulo"
        FORMATION = "FORMATION", "Formação"

    class Status(models.TextChoices):
        PREVIEW = "PREVIEW", "Prévia"
        PUBLISHED = "PUBLISHED", "Publicada"

    scope = models.CharField(max_length=20, choices=Scope.choices)
    formation = models.ForeignKey(SenseiFormation, on_delete=models.PROTECT, related_name="didactic_publications")
    module = models.ForeignKey(SenseiFormationModule, null=True, blank=True, on_delete=models.PROTECT, related_name="didactic_publications")
    unit = models.ForeignKey(SenseiStudyUnit, null=True, blank=True, on_delete=models.PROTECT, related_name="didactic_publications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREVIEW, db_index=True)
    preview_token = models.UUIDField(unique=True, editable=False)
    source_snapshot = models.JSONField(default=list)
    preview_payload = models.JSONField(default=list)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="didactic_publications")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class SenseiUnitStudyPlan(models.Model):
    unit = models.OneToOneField(SenseiStudyUnit, on_delete=models.CASCADE, related_name="study_plan")
    learning_objectives = models.JSONField(default=list)
    prerequisites = models.ManyToManyField(SenseiStudyUnit, blank=True, symmetrical=False, related_name="required_by_plans")
    related_competencies = models.ManyToManyField(SenseiCompetency, blank=True, related_name="study_plans")
    practices = models.JSONField(default=list)
    expected_evidence = models.JSONField(default=list)
    completion_criteria = models.JSONField(default=list)
    guidance = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SenseiStudyNote(models.Model):
    class NoteType(models.TextChoices):
        QUESTION = "QUESTION", "Dúvida"
        DISCOVERY = "DISCOVERY", "Descoberta"
        OWN_SUMMARY = "OWN_SUMMARY", "Resumo próprio"
        CONCEPT_LINK = "CONCEPT_LINK", "Relação com outro conceito"
        EXAMPLE = "EXAMPLE", "Exemplo"
        ERROR = "ERROR", "Erro encontrado"
        TECHNICAL_DECISION = "TECHNICAL_DECISION", "Decisão técnica"
        DEEP_DIVE_QUESTION = "DEEP_DIVE_QUESTION", "Pergunta para aprofundamento"

    unit = models.ForeignKey(SenseiStudyUnit, on_delete=models.CASCADE, related_name="study_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_study_notes")
    note_type = models.CharField(max_length=30, choices=NoteType.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]


class SenseiUnitStudyProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Não iniciada"
        STUDYING = "STUDYING", "Em estudo"
        STUDIED = "STUDIED", "Estudada"

    unit = models.ForeignKey(SenseiStudyUnit, on_delete=models.CASCADE, related_name="study_progress_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_unit_study_progress")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    started_at = models.DateTimeField(null=True, blank=True)
    studied_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["unit", "user"], name="unique_sensei_unit_study_progress")]


class SenseiStudyJourney(models.Model):
    """Persistent navigation state, deliberately independent from competency mastery."""

    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Não iniciada"
        IN_PROGRESS = "IN_PROGRESS", "Em andamento"
        COMPLETED = "COMPLETED", "Concluída"

    formation = models.ForeignKey(SenseiFormation, on_delete=models.CASCADE, related_name="study_journeys")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sensei_study_journeys")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    current_unit = models.ForeignKey(
        SenseiStudyUnit, null=True, blank=True, on_delete=models.SET_NULL, related_name="current_study_journeys"
    )
    last_position = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["formation", "user"], name="unique_sensei_study_journey"),
        ]

    def clean(self):
        super().clean()
        if self.current_unit_id and self.current_unit.module.formation_id != self.formation_id:
            raise ValidationError({"current_unit": "A unidade atual deve pertencer à formação da jornada."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
