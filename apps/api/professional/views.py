from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.http import HttpResponse

from ai.services import AIProviderError
from core.permissions import IsAdministrativeUser
from library.models import SenseiCompetency
from library.serializers import SenseiCompetencyEvidenceSerializer

from .models import Opportunity, OpportunityAnalysis, OpportunityBriefing, OpportunityExecutionArtifact, OpportunityExecutionPlan, OpportunityProposal, ProfessionalModality
from .serializers import (
    BriefingGenerationSerializer, OpportunityAnalysisSerializer, OpportunityBriefingSerializer,
    OpportunityExecutionArtifactSerializer, OpportunityExecutionPlanSerializer, OpportunityProposalSerializer, OpportunitySerializer,
    ProfessionalModalitySerializer, ProposalGenerationSerializer,
    ExecutionEvidenceSubmissionSerializer,
)
from .services import (
    InvalidBriefingResponse, InvalidProfessionalResponse, generate_intelligent_briefing,
    generate_opportunity_analysis, generate_opportunity_execution_plan, generate_opportunity_proposal,
    submit_execution_artifacts_as_competency_evidence,
)
from .exports import MIMES, export_filename, proposal_export_filename, render_export, render_proposal_export


class ProfessionalModalityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProfessionalModalitySerializer
    permission_classes = [IsAdministrativeUser]
    pagination_class = None

    def get_queryset(self):
        return ProfessionalModality.objects.filter(is_active=True).order_by("sort_order", "name")


class OpportunityViewSet(viewsets.ModelViewSet):
    serializer_class = OpportunitySerializer
    permission_classes = [IsAdministrativeUser]

    def get_queryset(self):
        queryset = Opportunity.objects.filter(created_by=self.request.user).prefetch_related("modalities")
        modality = self.request.query_params.get("modality")
        if modality:
            queryset = queryset.filter(modalities__slug=modality)
        return queryset.order_by("-created_at").distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="execution-artifacts")
    def execution_artifacts(self, request, pk=None):
        opportunity = self.get_object()
        if request.method == "GET":
            queryset = OpportunityExecutionArtifact.objects.filter(
                opportunity=opportunity,
                created_by=request.user,
            )
            serializer = OpportunityExecutionArtifactSerializer(queryset, many=True)
            return Response(serializer.data)
        serializer = OpportunityExecutionArtifactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(opportunity=opportunity, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="submit-execution-evidence")
    def submit_execution_evidence(self, request, pk=None):
        opportunity = self.get_object()
        serializer = ExecutionEvidenceSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        artifact_ids = set(data["artifact_ids"])
        matching_ids = set(OpportunityExecutionArtifact.objects.filter(
            opportunity=opportunity, pk__in=artifact_ids,
        ).values_list("pk", flat=True))
        if matching_ids != artifact_ids:
            raise ValidationError({"artifact_ids": "Artefatos inválidos para esta oportunidade."})
        # The service resolves this identifier and checks competency access.
        data["competency"] = SenseiCompetency(pk=data["competency"])
        evidence = submit_execution_artifacts_as_competency_evidence(user=request.user, **data)
        return Response(SenseiCompetencyEvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED)

    def _safe_generation_error(self, operation):
        try:
            return operation()
        except AIProviderError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except InvalidProfessionalResponse:
            return Response({"detail": "O provedor de IA retornou uma estrutura inválida.", "code": "invalid_response"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception:
            return Response({"detail": "Não foi possível concluir a geração com IA.", "code": "unknown"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        opportunity = self.get_object()
        if request.data:
            return Response({"detail": "A análise usa somente os dados persistidos da oportunidade."}, status=status.HTTP_400_BAD_REQUEST)

        def generate():
            payload, provider, model = generate_opportunity_analysis(opportunity)
            with transaction.atomic():
                analysis, _ = OpportunityAnalysis.objects.update_or_create(
                    opportunity=opportunity,
                    defaults={"created_by": request.user, "ai_provider": provider, "ai_model": model, **payload},
                )
                opportunity.status = Opportunity.Status.ANALYZING
                opportunity.save(update_fields=["status", "updated_at"])
            return Response(OpportunityAnalysisSerializer(analysis).data)

        return self._safe_generation_error(generate)

    @action(detail=True, methods=["get"], url_path="analysis")
    def analysis(self, request, pk=None):
        opportunity = self.get_object()
        try:
            analysis = opportunity.viability_analysis
        except OpportunityAnalysis.DoesNotExist:
            return Response({"detail": "A oportunidade ainda não foi analisada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OpportunityAnalysisSerializer(analysis).data)

    @action(detail=True, methods=["post"], url_path="generate-proposal")
    def generate_proposal(self, request, pk=None):
        opportunity = self.get_object()
        input_serializer = ProposalGenerationSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        version = input_serializer.validated_data["version"]
        try:
            analysis = opportunity.viability_analysis
        except OpportunityAnalysis.DoesNotExist:
            return Response({"detail": "Analise a oportunidade antes de gerar a proposta."}, status=status.HTTP_409_CONFLICT)
        existing = OpportunityProposal.objects.filter(opportunity=opportunity, version=version).first()
        if existing and existing.status == OpportunityProposal.Status.APPROVED:
            return Response({"detail": "A versão aprovada foi preservada e não pode ser regenerada.", "proposal": OpportunityProposalSerializer(existing).data}, status=status.HTTP_409_CONFLICT)

        def generate():
            payload, provider, model = generate_opportunity_proposal(opportunity, analysis, version)
            proposal, _ = OpportunityProposal.objects.update_or_create(
                opportunity=opportunity, version=version,
                defaults={"created_by": request.user, "status": OpportunityProposal.Status.DRAFT, "approved_at": None, "ai_provider": provider, "ai_model": model, **payload},
            )
            return Response(OpportunityProposalSerializer(proposal).data)

        return self._safe_generation_error(generate)

    def _proposal_version(self, request):
        value = request.query_params.get("version") if request.method == "GET" else request.data.get("version")
        return value if value in OpportunityProposal.Version.values else None

    @action(detail=True, methods=["get", "patch"], url_path="proposal")
    def proposal(self, request, pk=None):
        opportunity = self.get_object()
        version = self._proposal_version(request)
        if not version:
            return Response({"version": ["Informe SHORT, CONSULTATIVE ou TECHNICAL."]}, status=status.HTTP_400_BAD_REQUEST)
        proposal = OpportunityProposal.objects.filter(opportunity=opportunity, version=version).first()
        if not proposal:
            return Response({"detail": "Esta versão da proposta ainda não foi gerada."}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "GET":
            return Response(OpportunityProposalSerializer(proposal).data)
        if proposal.status == OpportunityProposal.Status.APPROVED:
            return Response({"detail": "A proposta aprovada é imutável."}, status=status.HTTP_409_CONFLICT)
        serializer = OpportunityProposalSerializer(proposal, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="proposal/approve")
    def approve_proposal(self, request, pk=None):
        opportunity = self.get_object()
        version = self._proposal_version(request)
        if not version:
            return Response({"version": ["Informe SHORT, CONSULTATIVE ou TECHNICAL."]}, status=status.HTTP_400_BAD_REQUEST)
        proposal = OpportunityProposal.objects.filter(opportunity=opportunity, version=version).first()
        if not proposal:
            return Response({"detail": "Esta versão da proposta ainda não foi gerada."}, status=status.HTTP_404_NOT_FOUND)
        if proposal.status != OpportunityProposal.Status.APPROVED:
            proposal.status = OpportunityProposal.Status.APPROVED
            proposal.approved_at = timezone.now()
            proposal.save(update_fields=["status", "approved_at", "updated_at"])
        return Response(OpportunityProposalSerializer(proposal).data)

    @action(detail=True, methods=["get"], url_path=r"proposal/export/(?P<export_format>pdf|docx)")
    def export_proposal(self, request, pk=None, export_format=None):
        opportunity = self.get_object()
        version = self._proposal_version(request)
        if not version:
            return Response({"version": ["Informe SHORT, CONSULTATIVE ou TECHNICAL."]}, status=status.HTTP_400_BAD_REQUEST)
        proposal = OpportunityProposal.objects.filter(opportunity=opportunity, version=version).first()
        if not proposal:
            return Response({"detail": "Esta versão da proposta ainda não foi gerada."}, status=status.HTTP_404_NOT_FOUND)
        content = render_proposal_export(proposal, export_format)
        response = HttpResponse(content, content_type=MIMES[export_format])
        response["Content-Disposition"] = f'attachment; filename="{proposal_export_filename(opportunity, version, export_format)}"'
        return response

    @action(detail=True, methods=["post"], url_path="generate-execution-plan")
    def generate_execution_plan(self, request, pk=None):
        opportunity = self.get_object()
        version = request.data.get("proposal_version")
        if version not in OpportunityProposal.Version.values:
            return Response({"proposal_version": ["Informe SHORT, CONSULTATIVE ou TECHNICAL."]}, status=status.HTTP_400_BAD_REQUEST)
        proposal = OpportunityProposal.objects.filter(opportunity=opportunity, version=version, status=OpportunityProposal.Status.APPROVED).first()
        if not proposal:
            return Response({"detail": "Aprove a proposta antes de gerar o plano."}, status=status.HTTP_409_CONFLICT)

        def generate():
            payload, provider, model = generate_opportunity_execution_plan(opportunity, proposal)
            plan, _ = OpportunityExecutionPlan.objects.update_or_create(
                opportunity=opportunity,
                defaults={"created_by": request.user, "status": "DRAFT", "ai_provider": provider, "ai_model": model, **payload},
            )
            return Response(OpportunityExecutionPlanSerializer(plan).data)

        return self._safe_generation_error(generate)

    @action(detail=True, methods=["get"], url_path="execution-plan")
    def execution_plan(self, request, pk=None):
        opportunity = self.get_object()
        try:
            plan = opportunity.execution_plan
        except OpportunityExecutionPlan.DoesNotExist:
            return Response({"detail": "O plano inicial ainda não foi gerado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OpportunityExecutionPlanSerializer(plan).data)

    @action(detail=True, methods=["post"], url_path="generate-briefing")
    def generate_briefing(self, request, pk=None):
        opportunity = self.get_object()
        if not opportunity.description.strip():
            return Response({"detail": "Adicione uma descrição antes de gerar o briefing."}, status=status.HTTP_400_BAD_REQUEST)
        input_serializer = BriefingGenerationSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            payload, provider, model = generate_intelligent_briefing(opportunity, input_serializer.validated_data["additional_context"])
        except AIProviderError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except InvalidBriefingResponse:
            return Response({"detail": "O provedor de IA retornou um briefing inválido.", "code": "invalid_response"}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception:
            return Response({"detail": "Não foi possível gerar o briefing inteligente.", "code": "unknown"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        with transaction.atomic():
            briefing, _ = OpportunityBriefing.objects.update_or_create(
                opportunity=opportunity,
                defaults={"created_by": request.user, "raw_source_text": opportunity.description, "ai_provider": provider, "ai_model": model, **payload},
            )
        return Response(OpportunityBriefingSerializer(briefing).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "patch"], url_path="briefing")
    def briefing(self, request, pk=None):
        opportunity = self.get_object()
        try:
            briefing = opportunity.intelligent_briefing
        except OpportunityBriefing.DoesNotExist:
            return Response({"detail": "Nenhum briefing inteligente foi gerado."}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "GET":
            return Response(OpportunityBriefingSerializer(briefing).data)
        serializer = OpportunityBriefingSerializer(briefing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path=r"briefing/export/(?P<export_format>pdf|docx|pptx|md|json)")
    def export_briefing(self, request, pk=None, export_format=None):
        opportunity = self.get_object()
        try:
            briefing = opportunity.intelligent_briefing
        except OpportunityBriefing.DoesNotExist:
            return Response({"detail": "Nenhum briefing inteligente foi gerado."}, status=status.HTTP_404_NOT_FOUND)
        content = render_export(briefing, export_format)
        response = HttpResponse(content, content_type=MIMES[export_format])
        response["Content-Disposition"] = f'attachment; filename="{export_filename(opportunity, export_format)}"'
        return response
