from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ProfessionalModality(models.Model):
    class Domain(models.TextChoices):
        SOFTWARE_DEVELOPMENT = "SOFTWARE_DEVELOPMENT", "Desenvolvimento de Software"
        DATA = "DATA", "Dados"
        AI_AUTOMATION = "AI_AUTOMATION", "IA / Automação"
        CLOUD_INFRA = "CLOUD_INFRA", "Cloud / Infra"
        MARKETING = "MARKETING", "Marketing"
        BUSINESS_SYSTEMS = "BUSINESS_SYSTEMS", "Negócios / Sistemas"
        OTHER = "OTHER", "Outros"

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    domain = models.CharField(max_length=30, choices=Domain.choices)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Opportunity(models.Model):
    class Source(models.TextChoices):
        FREELAS_99 = "99FREELAS", "99Freelas"
        WORKANA = "WORKANA", "Workana"
        UPWORK = "UPWORK", "Upwork"
        DIRECT_CLIENT = "DIRECT_CLIENT", "Cliente direto"
        REFERRAL = "REFERRAL", "Indicação"
        PROSPECTING = "PROSPECTING", "Prospecção"
        AGENCIA_3DS = "AGENCIA_3DS", "Agência 3DS"
        OWN_PROJECT = "OWN_PROJECT", "Projeto próprio"
        OTHER = "OTHER", "Outra"

    class Status(models.TextChoices):
        NEW = "NEW", "Nova"
        ANALYZING = "ANALYZING", "Em análise"
        INTERESTED = "INTERESTED", "Interessado"
        NEGOTIATING = "NEGOTIATING", "Negociando"
        PROPOSAL_SENT = "PROPOSAL_SENT", "Proposta enviada"
        WON = "WON", "Ganha"
        LOST = "LOST", "Perdida"
        REJECTED = "REJECTED", "Rejeitada"
        ARCHIVED = "ARCHIVED", "Arquivada"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="professional_opportunities",
        on_delete=models.CASCADE,
    )
    modalities = models.ManyToManyField(
        ProfessionalModality,
        related_name="opportunities",
        blank=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    source = models.CharField(max_length=20, choices=Source.choices)
    source_url = models.URLField(blank=True)
    client_name = models.CharField(max_length=200, blank=True)
    client_reference = models.CharField(max_length=255, blank=True)
    budget_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    budget_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="BRL")
    deadline = models.DateField(null=True, blank=True)
    proposal_deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["created_by", "-created_at"], name="opp_owner_created_idx")]

    def clean(self):
        if self.budget_min is not None and self.budget_min < 0:
            raise ValidationError({"budget_min": "O orçamento mínimo não pode ser negativo."})
        if self.budget_max is not None and self.budget_max < 0:
            raise ValidationError({"budget_max": "O orçamento máximo não pode ser negativo."})
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValidationError({"budget_max": "O orçamento máximo deve ser maior ou igual ao mínimo."})

    def __str__(self):
        return self.title


class OpportunityBriefing(models.Model):
    opportunity = models.OneToOneField(
        Opportunity,
        related_name="intelligent_briefing",
        on_delete=models.CASCADE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="professional_briefings",
        on_delete=models.CASCADE,
    )
    raw_source_text = models.TextField()
    problem = models.TextField(blank=True)
    objective = models.TextField(blank=True)
    target_audience = models.TextField(blank=True)
    deliverables = models.JSONField(default=list)
    functional_requirements = models.JSONField(default=list)
    non_functional_requirements = models.JSONField(default=list)
    integrations = models.JSONField(default=list)
    data_requirements = models.JSONField(default=list)
    infrastructure_requirements = models.JSONField(default=list)
    constraints = models.JSONField(default=list)
    dependencies = models.JSONField(default=list)
    assumptions = models.JSONField(default=list)
    scope_risks = models.JSONField(default=list)
    ambiguities = models.JSONField(default=list)
    client_questions = models.JSONField(default=list)
    acceptance_criteria = models.JSONField(default=list)
    ai_provider = models.CharField(max_length=80)
    ai_model = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Briefing: {self.opportunity.title}"


class OpportunityAnalysis(models.Model):
    class Decision(models.TextChoices):
        GO = "GO", "Go"
        CAUTION = "CAUTION", "Caution"
        NO_GO = "NO_GO", "No-go"

    opportunity = models.OneToOneField(Opportunity, related_name="viability_analysis", on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="professional_analyses", on_delete=models.CASCADE)
    decision = models.CharField(max_length=10, choices=Decision.choices)
    score = models.PositiveSmallIntegerField()
    problem_summary = models.TextField()
    client_need = models.TextField()
    likely_deliverables = models.JSONField(default=list)
    technologies = models.JSONField(default=list)
    required_competencies = models.JSONField(default=list)
    complexity = models.CharField(max_length=30)
    technical_risks = models.JSONField(default=list)
    commercial_risks = models.JSONField(default=list)
    ambiguities = models.JSONField(default=list)
    missing_information = models.JSONField(default=list)
    client_questions = models.JSONField(default=list)
    external_dependencies = models.JSONField(default=list)
    estimated_deadline = models.TextField()
    estimated_effort = models.JSONField(default=dict)
    ai_execution_fit = models.TextField()
    competency_gap = models.JSONField(default=dict)
    score_breakdown = models.JSONField(default=dict)
    pricing = models.JSONField(default=dict)
    limitations = models.JSONField(default=list)
    ai_provider = models.CharField(max_length=80)
    ai_model = models.CharField(max_length=120, blank=True)
    version = models.CharField(max_length=20, default="v1")
    generated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OpportunityProposal(models.Model):
    class Version(models.TextChoices):
        SHORT = "SHORT", "Curta"
        CONSULTATIVE = "CONSULTATIVE", "Consultiva"
        TECHNICAL = "TECHNICAL", "Técnica"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        APPROVED = "APPROVED", "Aprovada"

    opportunity = models.ForeignKey(Opportunity, related_name="proposals", on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="professional_proposals", on_delete=models.CASCADE)
    version = models.CharField(max_length=20, choices=Version.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    greeting = models.TextField()
    understanding = models.TextField()
    approach = models.TextField()
    deliverables = models.JSONField(default=list)
    deadline = models.TextField()
    suggested_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="BRL")
    essential_questions = models.JSONField(default=list)
    differentiators = models.JSONField(default=list)
    closing = models.TextField()
    ai_provider = models.CharField(max_length=80)
    ai_model = models.CharField(max_length=120, blank=True)
    generation_version = models.CharField(max_length=20, default="v1")
    generated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["opportunity", "version"], name="unique_opportunity_proposal_version")]


class OpportunityExecutionPlan(models.Model):
    opportunity = models.OneToOneField(Opportunity, related_name="execution_plan", on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="professional_execution_plans", on_delete=models.CASCADE)
    project = models.CharField(max_length=300)
    phases = models.JSONField(default=list)
    risks = models.JSONField(default=list)
    validation = models.JSONField(default=list)
    delivery = models.JSONField(default=list)
    status = models.CharField(max_length=10, default="DRAFT")
    ai_provider = models.CharField(max_length=80)
    ai_model = models.CharField(max_length=120, blank=True)
    version = models.CharField(max_length=20, default="v1")
    generated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OpportunityExecutionArtifact(models.Model):
    """Registro de trabalho realmente executado em uma oportunidade profissional."""

    class ArtifactType(models.TextChoices):
        CODE = "CODE", "Código"
        TEST = "TEST", "Teste"
        ARCHITECTURE = "ARCHITECTURE", "Arquitetura"
        TECHNICAL_DECISION = "TECHNICAL_DECISION", "Decisão técnica"
        DEBUGGING = "DEBUGGING", "Debugging"
        DOCUMENTATION = "DOCUMENTATION", "Documentação"
        DELIVERABLE = "DELIVERABLE", "Entregável"
        OTHER = "OTHER", "Outro"

    class Confidentiality(models.TextChoices):
        PRIVATE = "PRIVATE", "Privado"
        ANONYMIZED = "ANONYMIZED", "Pode ser usado de forma anonimizada"
        SHAREABLE = "SHAREABLE", "Pode ser compartilhado"

    opportunity = models.ForeignKey(
        Opportunity,
        related_name="execution_artifacts",
        on_delete=models.CASCADE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="professional_execution_artifacts",
        on_delete=models.PROTECT,
    )
    artifact_type = models.CharField(max_length=30, choices=ArtifactType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField()
    content = models.TextField(blank=True)
    reference_url = models.URLField(blank=True)
    confidentiality = models.CharField(
        max_length=20,
        choices=Confidentiality.choices,
        default=Confidentiality.PRIVATE,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["opportunity", "-created_at"],
                name="exec_artifact_opp_idx",
            )
        ]

    def __str__(self):
        return f"{self.get_artifact_type_display()}: {self.title}"


class OpportunityExecutionEvidenceLink(models.Model):
    artifact = models.ForeignKey(
        OpportunityExecutionArtifact,
        related_name="evidence_links",
        on_delete=models.CASCADE,
    )
    evidence = models.ForeignKey(
        "library.SenseiCompetencyEvidence",
        related_name="professional_execution_links",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["artifact", "evidence"], name="unique_exec_artifact_evidence"),
        ]

    def __str__(self):
        return f"{self.artifact_id} - {self.evidence_id}"
