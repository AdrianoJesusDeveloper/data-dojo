from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import (
    Book, ContentPackage, GeneratedScript, LibrarySource, ModernizationPlan,
    SourceCitation, StudioApproval, StudioProject, Trilha,
)


class LibrarySourceSerializer(serializers.ModelSerializer):
    duplicate = serializers.SerializerMethodField()

    class Meta:
        model = LibrarySource
        fields = (
            "id", "relative_path", "filename", "extension", "size_bytes", "sha256",
            "status", "modified_at", "discovered_at", "last_seen_at", "duplicate",
        )

    def get_duplicate(self, obj):
        return bool(obj.sha256 and LibrarySource.objects.filter(sha256=obj.sha256).exclude(pk=obj.pk).exists())


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
            "total_chunks", "error_message", "created_at", "processed_at",
        )
        read_only_fields = ("status", "total_chunks", "error_message", "created_at", "processed_at")

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
            "ganho_negocio", "estrutura", "conteudo_bruto", "created_by", "created_at",
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


class StudioProjectSerializer(serializers.ModelSerializer):
    modernization_plan = ModernizationPlanSerializer(read_only=True)
    citations = SourceCitationSerializer(many=True, read_only=True)
    approvals = StudioApprovalSerializer(many=True, read_only=True)
    content_package = ContentPackageSerializer(read_only=True)

    class Meta:
        model = StudioProject
        fields = (
            "id", "title", "theme", "objective", "source", "books", "status",
            "created_by", "created_at", "updated_at", "modernization_plan",
            "citations", "approvals", "content_package",
        )
        read_only_fields = ("status", "created_by", "created_at", "updated_at")


class ApprovalInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "revision"))
    notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)
