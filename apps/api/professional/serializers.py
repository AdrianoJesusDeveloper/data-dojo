from rest_framework import serializers

from .models import (
    Opportunity, OpportunityAnalysis, OpportunityBriefing, OpportunityExecutionArtifact, OpportunityExecutionPlan,
    OpportunityProposal, ProfessionalModality,
)


class ProfessionalModalitySerializer(serializers.ModelSerializer):
    domain_label = serializers.CharField(source="get_domain_display", read_only=True)

    class Meta:
        model = ProfessionalModality
        fields = ["id", "name", "slug", "domain", "domain_label", "is_active", "sort_order"]
        read_only_fields = fields


class OpportunitySerializer(serializers.ModelSerializer):
    modalities = ProfessionalModalitySerializer(many=True, read_only=True)
    modality_ids = serializers.PrimaryKeyRelatedField(
        source="modalities",
        many=True,
        queryset=ProfessionalModality.objects.filter(is_active=True),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Opportunity
        fields = [
            "id", "created_by", "title", "description", "source", "source_url",
            "client_name", "client_reference", "budget_min", "budget_max", "currency",
            "deadline", "proposal_deadline", "status", "notes", "modalities", "modality_ids",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Informe uma moeda com 3 letras, como BRL ou USD.")
        return value

    def validate(self, attrs):
        minimum = attrs.get("budget_min", getattr(self.instance, "budget_min", None))
        maximum = attrs.get("budget_max", getattr(self.instance, "budget_max", None))
        errors = {}
        if minimum is not None and minimum < 0:
            errors["budget_min"] = "O orçamento mínimo não pode ser negativo."
        if maximum is not None and maximum < 0:
            errors["budget_max"] = "O orçamento máximo não pode ser negativo."
        if minimum is not None and maximum is not None and minimum > maximum:
            errors["budget_max"] = "O orçamento máximo deve ser maior ou igual ao mínimo."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class OpportunityBriefingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityBriefing
        fields = [
            "id", "opportunity", "created_by", "raw_source_text", "problem", "objective",
            "target_audience", "deliverables", "functional_requirements",
            "non_functional_requirements", "integrations", "data_requirements",
            "infrastructure_requirements", "constraints", "dependencies", "assumptions",
            "scope_risks", "ambiguities", "client_questions", "acceptance_criteria",
            "ai_provider", "ai_model", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "opportunity", "created_by", "raw_source_text", "ai_provider", "ai_model", "created_at", "updated_at"]

    def validate(self, attrs):
        list_fields = (
            "deliverables", "functional_requirements", "non_functional_requirements",
            "integrations", "data_requirements", "infrastructure_requirements", "constraints",
            "dependencies", "assumptions", "scope_risks", "ambiguities", "client_questions",
            "acceptance_criteria",
        )
        errors = {}
        for field in list_fields:
            if field in attrs and (not isinstance(attrs[field], list) or any(not isinstance(item, str) for item in attrs[field])):
                errors[field] = "Informe uma lista de textos."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class BriefingGenerationSerializer(serializers.Serializer):
    additional_context = serializers.CharField(required=False, allow_blank=True, max_length=5000, default="")


class OpportunityAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityAnalysis
        fields = "__all__"
        read_only_fields = [field.name for field in OpportunityAnalysis._meta.fields]


class ProposalGenerationSerializer(serializers.Serializer):
    version = serializers.ChoiceField(choices=OpportunityProposal.Version.choices)


class OpportunityProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityProposal
        fields = "__all__"
        read_only_fields = [
            "id", "opportunity", "created_by", "version", "status", "ai_provider", "ai_model",
            "generation_version", "generated_at", "approved_at", "created_at", "updated_at",
        ]

    def validate_currency(self, value):
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise serializers.ValidationError("Informe uma moeda com 3 letras.")
        return normalized


class OpportunityExecutionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityExecutionPlan
        fields = "__all__"
        read_only_fields = [field.name for field in OpportunityExecutionPlan._meta.fields]


class OpportunityExecutionArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityExecutionArtifact
        fields = [
            "id", "opportunity", "created_by", "artifact_type", "title", "description",
            "content", "reference_url", "confidentiality", "metadata", "occurred_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "opportunity", "created_by", "created_at", "updated_at"]


class ExecutionEvidenceSubmissionSerializer(serializers.Serializer):
    artifact_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    competency = serializers.IntegerField(min_value=1)
    evidence_type = serializers.CharField()
    demonstrated_level = serializers.IntegerField()
    description = serializers.CharField()
    content = serializers.CharField(required=False, allow_blank=True, default="")
    reference_url = serializers.CharField(required=False, allow_blank=True, default="")
