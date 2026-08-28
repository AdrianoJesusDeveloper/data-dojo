from pathlib import Path
import json

from django.conf import settings
from rest_framework import serializers

from .models import (
    Book, ContentPackage, EditorialAgentRun, EditorialComment, EditorialCouncilRun, EditorialPlanVersion, GeneratedScript,
    LibrarySource, ModernizationPlan, SourceCitation, StudioApproval, StudioProject, Trilha,
)


class LibrarySourceSerializer(serializers.ModelSerializer):
    duplicate = serializers.BooleanField(source="_duplicate", read_only=True, default=False)
    book_id = serializers.IntegerField(source="book.id", read_only=True, default=None)
    book_status = serializers.CharField(source="book.status", read_only=True, default=None)
    book_error = serializers.SerializerMethodField()

    class Meta:
        model = LibrarySource
        fields = (
            "id", "relative_path", "filename", "extension", "size_bytes", "sha256",
            "status", "modified_at", "discovered_at", "last_seen_at", "duplicate",
            "book_id", "book_status", "book_error",
        )

    def get_book_error(self, obj):
        book = getattr(obj, "book", None)
        return "Falha no processamento do PDF. Consulte os logs do servidor." if book and book.error_message else ""


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
            "source", "total_chunks", "error_message", "created_at", "processed_at",
        )
        read_only_fields = ("source", "status", "total_chunks", "error_message", "created_at", "processed_at")

    def validate_file(self, value):
        if Path(value.name).suffix.lower() != ".pdf":
            raise serializers.ValidationError("Envie um arquivo PDF.")
        if value.size > settings.LIBRARY_MAX_UPLOAD_MB * 1024 * 1024:
            raise serializers.ValidationError(f"O PDF excede o limite de {settings.LIBRARY_MAX_UPLOAD_MB} MB.")
        header = value.read(5)
        value.seek(0)
        if header != b"%PDF-":
            raise serializers.ValidationError("O arquivo não possui uma assinatura PDF válida.")
        return value

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
        fields = ("id", "status", "total_chunks", "error_message", "processed_at")

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

    class Meta:
        model = StudioProject
        fields = (
            "id", "title", "theme", "objective", "project_type", "source", "books", "status",
            "created_by", "created_at", "updated_at", "modernization_plan",
            "citations", "approvals", "content_package", "editorial_comments",
            "is_archived", "archived_at",
        )
        read_only_fields = ("status", "created_by", "created_at", "updated_at", "is_archived", "archived_at")

    def validate_project_type(self, value):
        if self.instance and value != self.instance.project_type and hasattr(self.instance, "modernization_plan"):
            raise serializers.ValidationError("O tipo editorial nÃ£o pode ser alterado depois da primeira geraÃ§Ã£o do plano.")
        return value


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
