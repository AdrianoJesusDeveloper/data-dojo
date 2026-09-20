from pathlib import Path
import json
import re

from django.conf import settings
from rest_framework import serializers

from .models import (
    Book, ContentPackage, EditorialAgentRun, EditorialComment, EditorialCouncilRun, EditorialPlanVersion, GeneratedScript,
    DidacticLesson, DidacticLessonSection, LibrarySource, ModernizationPlan, SenseiCompetency, SenseiCompetencyEvidence, SenseiLearningActivity, SenseiLearningAttempt,
    SenseiCompetencyProgress, SenseiFormation, SenseiFormationModule, SenseiProgress,
    SenseiStudyJourney, SenseiStudyNote, SenseiStudyUnit, SenseiUnitSource, SenseiUnitSourceGap, SenseiUnitStudyPlan,
    SenseiUnitStudyProgress, SourceCitation, StudioApproval, StudioArtifact, StudioFormationLink,
    StudioProject, StudioResearchContext, StudioResearchEvidence, Trilha,
)

from .editorial_contracts import normalize_project_type

PDF_RANGE_RE = re.compile(
    r"PDF\s*p\.?\s*(\d+)\s*(?:a|até|-|–|—)\s*(\d+)",
    re.IGNORECASE,
)
PDF_SINGLE_RE = re.compile(r"PDF\s*p\.?\s*(\d+)", re.IGNORECASE)
PROVISIONAL_LOCATION_TOKENS = ("capítulo x", "capitulo x", "xx-yy", "xx–yy", "a confirmar", "pendente")


def parse_approved_pdf_ranges(location: str) -> list[dict]:
    location = (location or "").strip()
    ranges = []
    consumed = []

    for match in PDF_RANGE_RE.finditer(location):
        start = int(match.group(1))
        end = int(match.group(2))
        if end < start:
            start, end = end, start
        ranges.append({"pdf_start": start, "pdf_end": end})
        consumed.append(match.span())

    for match in PDF_SINGLE_RE.finditer(location):
        if any(left <= match.start() < right for left, right in consumed):
            continue
        page = int(match.group(1))
        ranges.append({"pdf_start": page, "pdf_end": page})

    unique = []
    seen = set()
    for item in ranges:
        key = (item["pdf_start"], item["pdf_end"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique



class LibrarySourceSerializer(serializers.ModelSerializer):
    duplicate = serializers.BooleanField(source="_duplicate", read_only=True, default=False)
    book_id = serializers.IntegerField(source="book.id", read_only=True, default=None)
    book_status = serializers.CharField(source="book.status", read_only=True, default=None)
    book_progress_percent = serializers.IntegerField(source="book.progress_percent", read_only=True, default=None)
    book_progress_stage = serializers.CharField(source="book.progress_stage", read_only=True, default="")
    book_error = serializers.SerializerMethodField()

    class Meta:
        model = LibrarySource
        fields = (
            "id", "relative_path", "filename", "extension", "size_bytes", "sha256",
            "status", "modified_at", "discovered_at", "last_seen_at", "duplicate",
            "book_id", "book_status", "book_progress_percent", "book_progress_stage", "book_error",
        )

    def get_book_error(self, obj):
        book = getattr(obj, "book", None)
        return "Falha no processamento do PDF. Consulte os logs do servidor." if book and book.error_message else ""


class DidacticLessonSectionSerializer(serializers.ModelSerializer):
    section_type_label = serializers.CharField(source="get_section_type_display", read_only=True)

    class Meta:
        model = DidacticLessonSection
        fields = ("id", "section_type", "section_type_label", "title", "content", "order", "metadata")
        read_only_fields = ("id", "section_type_label")


class DidacticLessonSerializer(serializers.ModelSerializer):
    sections = DidacticLessonSectionSerializer(many=True, read_only=True)
    source_ids = serializers.PrimaryKeyRelatedField(source="sources", many=True, read_only=True)
    source_provenance = serializers.SerializerMethodField()
    origin_lesson_id = serializers.IntegerField(read_only=True)
    workspace_lesson_id = serializers.IntegerField(read_only=True)
    student_is_stale = serializers.SerializerMethodField()

    class Meta:
        model = DidacticLesson
        fields = ("id", "title", "audience", "status", "source_mode", "learning_target_type", "learning_target_id", "ai_provider", "ai_model", "generated_at", "grounding_snapshot", "author", "reviewed_by", "reviewed_at", "published_at", "origin_lesson_id", "origin_updated_at", "workspace_lesson_id", "student_is_stale", "source_ids", "source_provenance", "sections", "created_at", "updated_at")
        read_only_fields = fields

    def get_source_provenance(self, lesson):
        return [{"id": source.id, "reference": source.reference, "category": source.category, "source_type": source.source_type, "priority": source.priority, "location": source.location, "approved_ranges": source.approved_ranges} for source in lesson.sources.all()]

    def get_student_is_stale(self, lesson):
        return bool(lesson.origin_lesson_id and lesson.origin_updated_at != lesson.origin_lesson.updated_at)


class DidacticLessonUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    status = serializers.ChoiceField(choices=DidacticLesson.Status.choices, required=False)
    sections = DidacticLessonSectionSerializer(many=True, required=False)


class DidacticPublicationPreviewSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=("LESSON", "MODULE", "FORMATION"))


class DidacticPublicationPublishSerializer(serializers.Serializer):
    preview_token = serializers.UUIDField()


class TrilhaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trilha
        fields = ("id", "nome", "foco", "ordem")


class BookSerializer(serializers.ModelSerializer):
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            "id", "title", "author", "trilha", "tecnologias", "file", "status",
            "source", "total_chunks", "progress_percent", "progress_stage",
            "error_message", "created_at", "processed_at",
        )
        read_only_fields = (
            "source", "status", "total_chunks", "progress_percent", "progress_stage",
            "error_message", "created_at", "processed_at",
        )

    def validate_file(self, value):
        extension = Path(value.name).suffix.lower()
        if extension not in {".pdf", ".epub", ".docx", ".txt"}:
            raise serializers.ValidationError("Envie PDF, EPUB, DOCX ou TXT.")
        if value.size > settings.LIBRARY_MAX_UPLOAD_MB * 1024 * 1024:
            raise serializers.ValidationError(f"O PDF excede o limite de {settings.LIBRARY_MAX_UPLOAD_MB} MB.")
        header = value.read(5)
        value.seek(0)
        if extension == ".pdf" and header != b"%PDF-":
            raise serializers.ValidationError("O arquivo não possui uma assinatura PDF válida.")
        if extension in {".epub", ".docx"}:
            import zipfile
            try:
                with zipfile.ZipFile(value) as archive:
                    expected = "META-INF/container.xml" if extension == ".epub" else "word/document.xml"
                    if expected not in archive.namelist():
                        raise ValueError()
            except (ValueError, zipfile.BadZipFile):
                raise serializers.ValidationError("O arquivo não possui uma estrutura válida.")
            finally:
                value.seek(0)
        return value

    def create(self, validated_data):
        from .services.book_storage import identity_lock, stream_hash, check_duplicate
        with identity_lock():
            digest = stream_hash(validated_data["file"])
            check_duplicate(digest)
            return Book.objects.create(**validated_data, sha256=digest)

    def get_error_message(self, obj):
        return "Falha no processamento do PDF. Consulte os logs do servidor." if obj.error_message else ""

    def validate_tecnologias(self, value):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError("tecnologias deve ser uma lista de textos.")
        return value


class BookStatusSerializer(serializers.ModelSerializer):
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            "id", "status", "total_chunks", "progress_percent", "progress_stage",
            "error_message", "processed_at",
        )

    def get_error_message(self, obj):
        return "Falha no processamento do PDF. Consulte os logs do servidor." if obj.error_message else ""


class GenerateScriptSerializer(serializers.Serializer):
    trilha_id = serializers.PrimaryKeyRelatedField(source="trilha", queryset=Trilha.objects.all())
    book_ids = serializers.PrimaryKeyRelatedField(source="books", queryset=Book.objects.all(), many=True)
    tema = serializers.CharField(max_length=500, trim_whitespace=True)

    def validate_books(self, books):
        if not books:
            raise serializers.ValidationError("Selecione ao menos um livro.")
        unavailable = [book.id for book in books if book.status != "ready"]
        if unavailable:
            raise serializers.ValidationError(f"Livros ainda não processados: {unavailable}.")
        return books


class GeneratedScriptSerializer(serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True)
    trilha = TrilhaSerializer(read_only=True)

    class Meta:
        model = GeneratedScript
        fields = (
            "id", "trilha", "books", "titulo_video", "problema_resolvido",
            "ganho_negocio", "estrutura", "created_by", "created_at",
        )
        read_only_fields = fields


class SourceCitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceCitation
        fields = ("id", "book_title", "page_number", "excerpt", "purpose", "created_at")


class ModernizationPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModernizationPlan
        exclude = ("raw_response",)
        read_only_fields = ("project", "version", "created_at", "updated_at")


class EditorialPlanVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = EditorialPlanVersion
        fields = ("id", "version", "content", "project_type", "origin", "state", "created_by_name", "created_at")
        read_only_fields = fields


class EditorialCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = EditorialComment
        fields = ("id", "text", "target", "target_type", "target_id", "plan_version", "resolved", "resolved_at", "author_name", "created_at")
        read_only_fields = ("id", "resolved", "resolved_at", "author_name", "created_at")

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("O comentÃ¡rio nÃ£o pode ficar vazio.")
        if len(value) > 10_000:
            raise serializers.ValidationError("O comentÃ¡rio excede o limite de 10.000 caracteres.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        target_type = attrs.get("target_type", "plan")
        if target_type in {"module", "lesson", "video", "section"} and not attrs.get("target_id", "").strip():
            raise serializers.ValidationError({"target_id": "Identifique o alvo editorial."})
        return attrs


class StudioApprovalSerializer(serializers.ModelSerializer):
    decided_by_name = serializers.CharField(source="decided_by.username", read_only=True)

    class Meta:
        model = StudioApproval
        fields = ("id", "artifact", "decision", "notes", "decided_by", "decided_by_name", "created_at")
        read_only_fields = ("decided_by", "decided_by_name", "created_at")


class ContentPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentPackage
        exclude = ("raw_response",)


class StudioResearchEvidenceSerializer(serializers.ModelSerializer):
    chunk_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = StudioResearchEvidence
        fields = ("id", "source_kind", "chunk_id", "url", "title", "domain", "source_type", "query", "excerpt", "retrieved_at", "metadata")
        read_only_fields = fields


class StudioResearchContextSerializer(serializers.ModelSerializer):
    evidence = StudioResearchEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = StudioResearchContext
        fields = ("id", "policy", "query", "dossier", "conflicts", "status", "built_at", "evidence")
        read_only_fields = fields


class StudioDossierSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import StudioDossierVersion
        model = StudioDossierVersion
        fields = ("id", "version", "based_on", "content", "research_policy", "references_snapshot", "status", "origin", "created_at", "reviewed_by", "reviewed_at")
        read_only_fields = fields


class StudioDossierInputSerializer(serializers.Serializer):
    content = serializers.JSONField()
    expected_version = serializers.IntegerField(min_value=0)
    evidence_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    inherit_references = serializers.BooleanField(required=False, default=True)


class StudioDossierTransitionInputSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=("REVIEW", "APPROVED"))


class StudioArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudioArtifact
        fields = ("id", "project", "artifact_type", "target_type", "target_id", "plan_version", "generation", "content", "status", "linked_unit", "linked_formation", "created_by", "reviewed_by", "reviewed_at", "created_at", "updated_at")
        read_only_fields = fields


class StudioArtifactTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("REVIEW", "APPROVED", "DRAFT"))


class StudioArtifactLinkSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(required=False, allow_null=True)
    formation_id = serializers.IntegerField(required=False, allow_null=True)


class StudioFormationLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudioFormationLink
        fields = ("id", "formation", "synced_plan_version", "identity_map", "synced_at")
        read_only_fields = fields


class EditorialAgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialAgentRun
        fields = ("id", "role", "status", "provider", "model", "output_payload", "rag_sources", "prompt_version", "started_at", "completed_at", "error_code")
        read_only_fields = fields


class EditorialCouncilRunSerializer(serializers.ModelSerializer):
    agent_runs = EditorialAgentRunSerializer(many=True, read_only=True)

    class Meta:
        model = EditorialCouncilRun
        fields = ("id", "project", "plan_version", "status", "final_synthesis", "error_code", "started_at", "heartbeat_at", "lease_expires_at", "completed_at", "created_at", "updated_at", "agent_runs")
        read_only_fields = fields


class StudioProjectSerializer(serializers.ModelSerializer):
    modernization_plan = ModernizationPlanSerializer(read_only=True)
    citations = SourceCitationSerializer(many=True, read_only=True)
    approvals = StudioApprovalSerializer(many=True, read_only=True)
    content_package = ContentPackageSerializer(read_only=True)
    editorial_comments = EditorialCommentSerializer(many=True, read_only=True)
    research_context = StudioResearchContextSerializer(read_only=True)
    artifacts = StudioArtifactSerializer(many=True, read_only=True)
    formation_link = StudioFormationLinkSerializer(read_only=True)

    class Meta:
        model = StudioProject
        fields = (
            "id", "title", "theme", "objective", "original_intent", "project_type",
            "production_channel", "production_format", "research_policy", "source", "books", "status",
            "created_by", "created_at", "updated_at", "modernization_plan",
            "citations", "approvals", "content_package", "editorial_comments",
            "is_archived", "archived_at", "research_context", "artifacts", "formation_link",
        )
        read_only_fields = ("status", "created_by", "created_at", "updated_at", "is_archived", "archived_at")

    def validate_project_type(self, value):
        if self.instance and value != self.instance.project_type and hasattr(self.instance, "modernization_plan"):
            raise serializers.ValidationError("O tipo editorial nÃ£o pode ser alterado depois da primeira geraÃ§Ã£o do plano.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        current_channel = getattr(self.instance, "production_channel", "") if self.instance else ""
        current_format = getattr(self.instance, "production_format", "") if self.instance else ""
        current_project_type = getattr(self.instance, "project_type", "premium") if self.instance else "premium"

        channel = attrs.get("production_channel", current_channel)
        production_format = attrs.get("production_format", current_format)
        project_type = attrs.get("project_type", current_project_type)
        semantic_project_type = normalize_project_type(project_type)

        # Canal e formato formam um par. Projetos legados podem manter ambos vazios.
        if bool(channel) != bool(production_format):
            raise serializers.ValidationError({
                "production_channel": "Informe canal e formato de produção juntos.",
                "production_format": "Informe canal e formato de produção juntos.",
            })

        # Formação Premium continua usando o fluxo Premium já existente.
        if channel == "premium" and semantic_project_type != "formation":
            raise serializers.ValidationError({
                "project_type": "Produções do canal Formação Premium devem usar o tipo editorial Premium."
            })
        if semantic_project_type == "formation" and channel and channel != "premium":
            raise serializers.ValidationError({
                "production_channel": "Projetos editoriais Premium só podem usar o canal Formação Premium."
            })

        # Depois do primeiro plano, canal/formato passam a integrar a identidade editorial
        # e não podem ser trocados silenciosamente.
        if self.instance and hasattr(self.instance, "modernization_plan"):
            if channel != current_channel:
                raise serializers.ValidationError({
                    "production_channel": "O canal de produção não pode ser alterado depois da primeira geração do plano."
                })
            if production_format != current_format:
                raise serializers.ValidationError({
                    "production_format": "O formato de produção não pode ser alterado depois da primeira geração do plano."
                })

        return attrs


class ApprovalInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "revision"))
    notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)


class EditorialPlanEditSerializer(serializers.Serializer):
    plan = serializers.JSONField()

    def validate_plan(self, value):
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 2 * 1024 * 1024:
            raise serializers.ValidationError("O plano excede o limite de 2 MB.")
        return value


class ContentGenerationInputSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=("lesson", "module", "video"))
    target_index = serializers.IntegerField(min_value=0)


class SenseiProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SenseiProgress
        fields = ("id", "formation", "user", "percentage", "state", "started_at", "completed_at", "created_at", "updated_at")
        read_only_fields = fields


class SenseiFormationSerializer(serializers.ModelSerializer):
    module_count = serializers.IntegerField(source="modules.count", read_only=True)
    competency_count = serializers.IntegerField(source="competencies.count", read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = SenseiFormation
        fields = ("id", "title", "slug", "description", "objective", "status", "source_policy", "level", "created_by", "created_at", "updated_at", "module_count", "competency_count", "progress")
        read_only_fields = ("id", "created_by", "created_at", "updated_at", "module_count", "competency_count", "progress")

    def get_progress(self, formation):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        progress = formation.progress_records.filter(user=request.user).first()
        return SenseiProgressSerializer(progress).data if progress else None


class SenseiFormationModuleSerializer(serializers.ModelSerializer):
    unit_count = serializers.IntegerField(source="study_units.count", read_only=True)
    study_units = serializers.SerializerMethodField()

    class Meta:
        model = SenseiFormationModule
        fields = ("id", "formation", "title", "description", "order", "unit_count", "study_units")
        read_only_fields = ("id", "formation", "unit_count", "study_units")

    def get_study_units(self, module):
        return [{"id": unit.id, "title": unit.title, "objective": unit.objective, "order": unit.order, "status": unit.status} for unit in module.study_units.all()]


class SenseiStudyUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SenseiStudyUnit
        fields = ("id", "module", "title", "objective", "order", "status", "sources", "reference_links")
        read_only_fields = ("id", "module")

    def validate_reference_links(self, value):
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise serializers.ValidationError("Informe uma lista de referências estruturadas.")
        return value


class SenseiCompetencySerializer(serializers.ModelSerializer):
    expected_level_label = serializers.CharField(source="get_expected_level_display", read_only=True)
    evidence_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = SenseiCompetency
        fields = ("id", "formation", "module", "title", "description", "expected_level", "expected_level_label", "mastery_criteria", "order", "evidence_count", "progress")
        read_only_fields = ("id", "formation", "expected_level_label", "evidence_count", "progress")

    def get_evidence_count(self, competency):
        request = self.context.get("request")
        return competency.evidences.filter(submitted_by=request.user).count() if request and request.user.is_authenticated else 0

    def get_progress(self, competency):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        progress = competency.progress_records.filter(user=request.user).first()
        return SenseiCompetencyProgressSerializer(progress).data if progress else None

    def validate_mastery_criteria(self, value):
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
            raise serializers.ValidationError("Informe critérios de domínio como uma lista não vazia de textos.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        formation = self.context.get("formation") or getattr(self.instance, "formation", None)
        module = attrs.get("module", getattr(self.instance, "module", None))
        if module and formation and module.formation_id != formation.id:
            raise serializers.ValidationError({"module": "O módulo deve pertencer à formação."})
        return attrs


class SenseiCompetencyEvidenceSerializer(serializers.ModelSerializer):
    evidence_type_label = serializers.CharField(source="get_evidence_type_display", read_only=True)
    demonstrated_level_label = serializers.CharField(source="get_demonstrated_level_display", read_only=True)

    class Meta:
        model = SenseiCompetencyEvidence
        fields = ("id", "competency", "submitted_by", "evidence_type", "evidence_type_label", "description", "content", "reference_url", "demonstrated_level", "demonstrated_level_label", "validation_status", "feedback", "validated_by", "validated_at", "created_at", "updated_at")
        read_only_fields = ("id", "competency", "submitted_by", "evidence_type_label", "demonstrated_level_label", "validation_status", "feedback", "validated_by", "validated_at", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        content = attrs.get("content", "").strip()
        reference = attrs.get("reference_url", "").strip()
        if not content and not reference:
            raise serializers.ValidationError("A evidência precisa de conteúdo ou referência.")
        return attrs


class SenseiEvidenceReviewSerializer(serializers.Serializer):
    validation_status = serializers.ChoiceField(choices=(SenseiCompetencyEvidence.ValidationStatus.VALIDATED, SenseiCompetencyEvidence.ValidationStatus.REJECTED))
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=10000)


class SenseiCompetencyProgressSerializer(serializers.ModelSerializer):
    current_level_label = serializers.SerializerMethodField()

    class Meta:
        model = SenseiCompetencyProgress
        fields = ("id", "competency", "user", "current_level", "current_level_label", "state", "updated_at")
        read_only_fields = ("id", "competency", "user", "current_level_label", "updated_at")

    def get_current_level_label(self, progress):
        return dict(SenseiCompetency.MasteryLevel.choices).get(progress.current_level, "Não demonstrado")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        progress = self.instance
        level = attrs.get("current_level", progress.current_level)
        state = attrs.get("state", progress.state)
        evidence_exists = progress.competency.evidences.filter(
            submitted_by=progress.user,
            validation_status=SenseiCompetencyEvidence.ValidationStatus.VALIDATED,
            demonstrated_level__gte=level,
        ).exists()
        if level > 0 and not evidence_exists:
            raise serializers.ValidationError({"current_level": "O nível exige evidência validada por uma pessoa."})
        if state == SenseiCompetencyProgress.State.DEMONSTRATED and level < progress.competency.expected_level:
            raise serializers.ValidationError({"state": "A competência ainda não atingiu o nível esperado."})
        if state == SenseiCompetencyProgress.State.TEACHING_READY and level < SenseiCompetency.MasteryLevel.TEACHES:
            raise serializers.ValidationError({"state": "Aptidão para ensinar exige o nível ENSINA."})
        if state == SenseiCompetencyProgress.State.NOT_STARTED and level != 0:
            raise serializers.ValidationError({"state": "Uma competência não iniciada não pode possuir nível demonstrado."})
        return attrs


class SenseiUnitSourceSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    source_type_label = serializers.CharField(source="get_source_type_display", read_only=True)

    class Meta:
        model = SenseiUnitSource
        fields = ("id", "unit", "source", "category", "category_label", "source_type", "source_type_label", "title", "reference", "location", "approved_ranges", "objective", "priority", "notes", "is_required", "url", "author_or_organization", "publication_date", "accessed_at", "source_updated_at", "justification", "confidence", "reliability_notes", "editorial_status", "rejection_reason", "reviewed_by", "reviewed_at", "created_at", "updated_at")
        read_only_fields = ("id", "unit", "category_label", "source_type_label", "editorial_status", "rejection_reason", "reviewed_by", "reviewed_at", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("source") and not attrs.get("url") and not attrs.get("reference", "").strip():
            raise serializers.ValidationError("Informe uma fonte local, URL ou referência identificável.")
        location = attrs.get("location", "")
        if attrs.get("source"):
            attrs["approved_ranges"] = parse_approved_pdf_ranges(location)
        elif "location" in attrs:
            attrs["approved_ranges"] = []
        return attrs


class SenseiUnitSourceReviewSerializer(serializers.Serializer):
    editorial_status = serializers.ChoiceField(choices=(SenseiUnitSource.EditorialStatus.APPROVED, SenseiUnitSource.EditorialStatus.REJECTED))
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        proposal = self.context["proposal"]
        if attrs["editorial_status"] == SenseiUnitSource.EditorialStatus.APPROVED:
            if not proposal.justification.strip() or not (proposal.source_id or proposal.url or proposal.reference.strip()):
                raise serializers.ValidationError("Aprovação exige justificativa e proveniência identificável.")
            if not proposal.location.strip():
                raise serializers.ValidationError("Aprovação exige capítulo, seção, páginas ou trecho confirmado por revisão humana.")
            lowered = proposal.location.lower()
            if any(token in lowered for token in PROVISIONAL_LOCATION_TOKENS):
                raise serializers.ValidationError("A localização ainda contém marcador provisório. Confirme capítulo e páginas reais antes de aprovar.")
            if proposal.source_id:
                if not proposal.approved_ranges:
                    raise serializers.ValidationError("Fonte local exige ao menos um intervalo estruturado no formato 'PDF p.122 a 135'.")
                linked_book = Book.objects.filter(source_id=proposal.source_id).first()
                if linked_book is not None:
                    max_page = linked_book.chunks.exclude(page_number__isnull=True).order_by("-page_number").values_list("page_number", flat=True).first()
                    if max_page and any(int(item.get("pdf_end", 0)) > max_page for item in proposal.approved_ranges):
                        raise serializers.ValidationError(f"A localização aprovada excede a última página processada do PDF ({max_page}).")
        elif not attrs.get("rejection_reason", "").strip():
            raise serializers.ValidationError({"rejection_reason": "Informe o motivo da rejeição."})
        return attrs


class SenseiUnitSourceGapSerializer(serializers.ModelSerializer):
    class Meta:
        model = SenseiUnitSourceGap
        fields = ("id", "unit", "status", "reason", "requirements", "notes", "created_by", "resolved_by", "resolved_at", "created_at", "updated_at")
        read_only_fields = ("id", "unit", "created_by", "resolved_by", "resolved_at", "created_at", "updated_at")


class SenseiStudyNoteSerializer(serializers.ModelSerializer):
    note_type_label = serializers.CharField(source="get_note_type_display", read_only=True)

    class Meta:
        model = SenseiStudyNote
        fields = ("id", "unit", "author", "note_type", "note_type_label", "content", "created_at", "updated_at")
        read_only_fields = ("id", "unit", "author", "note_type_label", "created_at", "updated_at")

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A anotação não pode ficar vazia.")
        return value


class SenseiUnitStudyProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SenseiUnitStudyProgress
        fields = ("id", "unit", "user", "status", "started_at", "studied_at", "updated_at")
        read_only_fields = ("id", "unit", "user", "started_at", "studied_at", "updated_at")


class SenseiStudyJourneySerializer(serializers.ModelSerializer):
    current_unit = SenseiStudyUnitSerializer(read_only=True)

    class Meta:
        model = SenseiStudyJourney
        fields = (
            "id", "formation", "user", "status", "started_at", "current_unit",
            "last_position", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "formation", "user", "status", "started_at", "current_unit",
            "created_at", "updated_at",
        )

    def validate_last_position(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("A última posição deve ser um objeto estruturado.")
        return value


class SenseiLearningAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SenseiLearningAttempt
        fields = ("id", "attempt_number", "answer", "feedback", "outcome", "identified_gap", "next_step", "metadata", "ai_provider", "ai_model", "submitted_at", "created_at")
        read_only_fields = fields


class SenseiLearningActivitySerializer(serializers.ModelSerializer):
    activity_type_label = serializers.CharField(source="get_activity_type_display", read_only=True)
    difficulty_label = serializers.CharField(source="get_difficulty_level_display", read_only=True)
    competency_title = serializers.CharField(source="competency.title", read_only=True)
    attempts = SenseiLearningAttemptSerializer(many=True, read_only=True)

    class Meta:
        model = SenseiLearningActivity
        fields = (
            "id", "unit", "competency", "competency_title", "activity_type", "activity_type_label",
            "prompt", "difficulty_level", "difficulty_label", "pedagogical_context", "learner_response",
            "feedback", "feedback_metadata", "ai_provider", "ai_model", "state", "attempts", "answered_at", "reviewed_at", "created_at", "updated_at",
        )
        read_only_fields = fields


class SenseiLearningAnswerSerializer(serializers.Serializer):
    response = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=20000)


class SenseiLearningProviderPreferenceSerializer(serializers.Serializer):
    provider = serializers.CharField(max_length=40, trim_whitespace=True)


class SenseiUnitStudyPlanSerializer(serializers.ModelSerializer):
    prerequisites = SenseiStudyUnitSerializer(many=True, read_only=True)
    related_competencies = SenseiCompetencySerializer(many=True, read_only=True)
    prerequisite_ids = serializers.PrimaryKeyRelatedField(source="prerequisites", queryset=SenseiStudyUnit.objects.all(), many=True, write_only=True, required=False)
    related_competency_ids = serializers.PrimaryKeyRelatedField(source="related_competencies", queryset=SenseiCompetency.objects.all(), many=True, write_only=True, required=False)
    curated_sources = serializers.SerializerMethodField()
    source_proposals = serializers.SerializerMethodField()
    source_gap = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    study_progress = serializers.SerializerMethodField()

    class Meta:
        model = SenseiUnitStudyPlan
        fields = ("id", "unit", "learning_objectives", "prerequisites", "prerequisite_ids", "related_competencies", "related_competency_ids", "practices", "expected_evidence", "completion_criteria", "guidance", "curated_sources", "source_proposals", "source_gap", "notes", "study_progress", "created_at", "updated_at")
        read_only_fields = ("id", "unit", "prerequisites", "related_competencies", "curated_sources", "source_proposals", "source_gap", "notes", "study_progress", "created_at", "updated_at")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        formation_id = self.instance.unit.module.formation_id
        prerequisites = attrs.get("prerequisites", [])
        if any(item.id == self.instance.unit_id or item.module.formation_id != formation_id for item in prerequisites):
            raise serializers.ValidationError({"prerequisite_ids": "Pré-requisitos devem ser outras unidades da mesma formação."})
        competencies = attrs.get("related_competencies", [])
        if any(item.formation_id != formation_id for item in competencies):
            raise serializers.ValidationError({"related_competency_ids": "Competências devem pertencer à mesma formação."})
        return attrs

    def get_notes(self, plan):
        request = self.context.get("request")
        return SenseiStudyNoteSerializer(plan.unit.study_notes.filter(author=request.user), many=True).data

    def get_study_progress(self, plan):
        request = self.context.get("request")
        progress = plan.unit.study_progress_records.filter(user=request.user).first()
        return SenseiUnitStudyProgressSerializer(progress).data if progress else {"status": "NOT_STARTED"}

    def get_curated_sources(self, plan):
        sources = plan.unit.curated_sources.filter(editorial_status=SenseiUnitSource.EditorialStatus.APPROVED).order_by("priority", "id")
        return SenseiUnitSourceSerializer(sources, many=True).data

    def get_source_proposals(self, plan):
        return SenseiUnitSourceSerializer(plan.unit.curated_sources.all(), many=True).data

    def get_source_gap(self, plan):
        gap = getattr(plan.unit, "source_gap", None)
        return SenseiUnitSourceGapSerializer(gap).data if gap else None
