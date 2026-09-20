from pathlib import Path
import logging
import json
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.db import transaction
from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Book, ContentPackage, DidacticLesson, DidacticPublication, EditorialComment, EditorialCouncilRun, EditorialPlanVersion, GeneratedScript,
    LibrarySource, ModernizationPlan, SenseiCompetency, SenseiCompetencyEvidence, SenseiLearningActivity,
    SenseiCompetencyProgress, SenseiFormation, SenseiFormationModule, SenseiProgress,
    SenseiStudyJourney, SenseiStudyNote, SenseiStudyUnit, SenseiUnitSource, SenseiUnitSourceGap, SenseiUnitStudyPlan,
    SenseiUnitStudyProgress, SourceCitation, StudioApproval, StudioArtifact, StudioProject, Trilha, DidacticLessonSection,
    SenseiLearningProviderPreference,
)
from .permissions import IsLocalStudioAdmin
from .serializers import (
    BookSerializer, BookStatusSerializer, DidacticLessonSerializer, DidacticLessonSectionSerializer, DidacticLessonUpdateSerializer, DidacticPublicationPreviewSerializer, DidacticPublicationPublishSerializer, GeneratedScriptSerializer, LibrarySourceSerializer,
    ApprovalInputSerializer, ContentGenerationInputSerializer, ContentPackageSerializer,
    EditorialCommentSerializer, EditorialCouncilRunSerializer, EditorialPlanEditSerializer, EditorialPlanVersionSerializer,
    GenerateScriptSerializer, SenseiCompetencyEvidenceSerializer, SenseiCompetencyProgressSerializer,
    SenseiCompetencySerializer, SenseiEvidenceReviewSerializer, SenseiFormationModuleSerializer,
    SenseiFormationSerializer, SenseiLearningActivitySerializer, SenseiLearningAnswerSerializer, SenseiLearningProviderPreferenceSerializer, SenseiProgressSerializer, SenseiStudyJourneySerializer, SenseiStudyNoteSerializer,
    SenseiStudyUnitSerializer, SenseiUnitSourceGapSerializer, SenseiUnitSourceReviewSerializer,
    SenseiUnitSourceSerializer, SenseiUnitStudyPlanSerializer,
    SenseiUnitStudyProgressSerializer,
    StudioArtifactLinkSerializer, StudioArtifactSerializer, StudioArtifactTransitionSerializer, StudioProjectSerializer, StudioResearchContextSerializer, TrilhaSerializer,
)
from .services.generation import gerar_roteiro
from .services.retrieval import buscar_chunks_relevantes
from .services.catalog import scan_library
from .editorial_contracts import normalize_project_type, validate_editorial_plan
from .services.studio_agents import (
    generate_content_item,
    generate_content_package,
    generate_modernization_plan,
    prepare_modernization_plan_request,
)
from .services.editorial_council import CouncilExecutionError, start_editorial_council
from .services.council_export import COUNCIL_EXPORT_MIMES, council_export_filename, render_council_export
from .services.sensei_learning import SenseiLearningError, available_providers, generate_activity, resolve_provider, review_response
from .services.didactic_content import DidacticContentError, generate_didactic_lesson, get_authorship_activity, get_authorship_section, start_authorship_challenge, update_human_lesson
from .services.claim_grounding import has_editorial_claim_state
from .services.didactic_export import build_export_snapshot, export_filename, render_lesson_docx, render_lesson_html
from .services.didactic_publication import DidacticPublicationError, create_preview, publish_preview
from .services.studio_export import artifact_filename, render_artifact_docx, render_artifact_html
from .services.studio_plan_export import MIMES as PLAN_EXPORT_MIMES, export_filename as plan_export_filename, render_plan_export
from .services.studio_section_export import SECTION_EXPORT_MIMES, section_export_filename, render_section_export
from .services.studio_formation import StudioFormationError, materialize_premium_formation
from .services.studio_research import StudioResearchError, build_research_context, generate_grounded_dossier, research_prompt_context
from ai.services import (
    AIProviderError,
    SENSEI_PROVIDER_CATALOG,
    canonical_provider_name,
    get_provider_model,
    provider_is_available,
)
from .tasks import process_book
from .serializers import StudioDossierSerializer, StudioDossierInputSerializer, StudioDossierTransitionInputSerializer
from .services.studio_dossier import create_dossier_version, transition_dossier_version, prepare_dossier_from_research


logger = logging.getLogger(__name__)


PLAN_STRUCTURED_OUTPUT_PROVIDERS = {"openai", "groq"}
CONTENT_STRUCTURED_OUTPUT_PROVIDERS = {"openai", "groq"}


class StudioPlanProviderSelectionError(ValueError):
    def __init__(self, detail: str, *, code: str, status_code: int):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code


def _resolve_plan_provider(raw_provider):
    if raw_provider in (None, ""):
        raw_provider = getattr(settings, "CONTENT_STUDIO_PROVIDER", "")

    if not isinstance(raw_provider, str):
        raise StudioPlanProviderSelectionError(
            "O provider selecionado é inválido.",
            code="invalid_provider",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    canonical = canonical_provider_name(raw_provider.strip())
    if not canonical or canonical not in SENSEI_PROVIDER_CATALOG:
        raise StudioPlanProviderSelectionError(
            "O provider selecionado não é reconhecido.",
            code="invalid_provider",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if canonical not in PLAN_STRUCTURED_OUTPUT_PROVIDERS:
        raise StudioPlanProviderSelectionError(
            "Este provider ainda não está habilitado para geração estruturada de planos.",
            code="unsupported_for_plan",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not provider_is_available(canonical):
        raise StudioPlanProviderSelectionError(
            "O provider selecionado não está configurado neste ambiente.",
            code="provider_unavailable",
            status_code=status.HTTP_409_CONFLICT,
        )

    return canonical


def _plan_provider_metadata(provider_name):
    metadata = SENSEI_PROVIDER_CATALOG[provider_name]
    available = provider_is_available(provider_name)
    structured_output = provider_name in PLAN_STRUCTURED_OUTPUT_PROVIDERS
    return {
        "id": provider_name,
        "label": metadata["label"],
        "model": get_provider_model(provider_name),
        "available": available,
        "structured_output": structured_output,
        "selectable_for_plan": available and structured_output,
    }


class StudioContentProviderSelectionError(ValueError):
    def __init__(self, detail: str, *, code: str, status_code: int):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code


def _resolve_content_provider(raw_provider):
    if raw_provider in (None, ""):
        raw_provider = getattr(settings, "CONTENT_STUDIO_PROVIDER", "")

    if not isinstance(raw_provider, str):
        raise StudioContentProviderSelectionError(
            "O provider selecionado é inválido.",
            code="invalid_provider",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    canonical = canonical_provider_name(raw_provider.strip())
    if not canonical or canonical not in SENSEI_PROVIDER_CATALOG:
        raise StudioContentProviderSelectionError(
            "O provider selecionado não é reconhecido.",
            code="invalid_provider",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if canonical not in CONTENT_STRUCTURED_OUTPUT_PROVIDERS:
        raise StudioContentProviderSelectionError(
            "Este provider ainda não está habilitado para geração estruturada de conteúdo.",
            code="unsupported_for_content",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not provider_is_available(canonical):
        raise StudioContentProviderSelectionError(
            "O provider selecionado não está configurado neste ambiente.",
            code="provider_unavailable",
            status_code=status.HTTP_409_CONFLICT,
        )

    return canonical


def _content_provider_metadata(provider_name):
    metadata = SENSEI_PROVIDER_CATALOG[provider_name]
    available = provider_is_available(provider_name)
    structured_output = provider_name in CONTENT_STRUCTURED_OUTPUT_PROVIDERS
    return {
        "id": provider_name,
        "label": metadata["label"],
        "model": get_provider_model(provider_name),
        "available": available,
        "structured_output": structured_output,
        "selectable_for_content": available and structured_output,
    }


def _prepare_plan_generation_inputs(project):
    """Resolve fontes/contexto localmente sem chamar provider externo."""
    approved_context = None
    if project.dossier_versions.filter(
        status="APPROVED",
        research_policy=project.research_policy,
    ).exists():
        approved_context = json.loads(research_prompt_context(project))

    use_snapshot = bool(
        approved_context and approved_context.get("documentary_grounding")
    )
    books = list(project.books.filter(status="ready"))

    if project.research_policy == "ACERVO_ONLY" and not books and not use_snapshot:
        raise ValueError("Vincule ao menos um livro processado ao projeto.")

    chunks = (
        buscar_chunks_relevantes(
            f"{project.theme}\n{project.objective}",
            [book.id for book in books],
            top_k=10,
        )
        if books and not use_snapshot and project.research_policy != "WEB_ONLY"
        else []
    )

    if project.research_policy == "ACERVO_ONLY" and not chunks and not use_snapshot:
        raise ValueError("Nenhuma fonte relevante foi recuperada.")

    grounded_context = (
        json.dumps(approved_context, ensure_ascii=False)
        if approved_context
        else ""
    )

    if not approved_context and hasattr(project, "research_context"):
        try:
            grounded_context = research_prompt_context(project)
        except StudioResearchError:
            if project.research_policy == "ACERVO_ONLY":
                raise
            grounded_context = ""

    return {
        "approved_context": approved_context,
        "use_snapshot": use_snapshot,
        "books": books,
        "chunks": chunks,
        "grounded_context": grounded_context,
    }


def _restore_project_after_plan_failure(project_id, expected_version):
    with transaction.atomic():
        locked_project = StudioProject.objects.select_for_update().get(pk=project_id)
        current = ModernizationPlan.objects.filter(project=locked_project).first()
        current_version = current.version if current else 0
        if (
            locked_project.status == "planning"
            and current_version == expected_version
        ):
            locked_project.status = "draft"
            locked_project.save(update_fields=["status", "updated_at"])


class StudioCouncilRunListCreateView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        runs = project.council_runs.prefetch_related("agent_runs")[:50]
        return Response(EditorialCouncilRunSerializer(runs, many=True).data)

    def post(self, request, pk):
        generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        try:
            run = start_editorial_council(pk, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except CouncilExecutionError:
            return Response({"detail": "O Conselho Editorial falhou de forma segura."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(EditorialCouncilRunSerializer(run).data, status=status.HTTP_201_CREATED)


class StudioCouncilExportView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk, export_format):
        if export_format not in COUNCIL_EXPORT_MIMES:
            return Response(
                {"detail": "Formato de exportação não suportado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        run = generics.get_object_or_404(
            EditorialCouncilRun.objects.select_related("project", "created_by")
            .prefetch_related("agent_runs"),
            pk=pk,
            project__created_by=request.user,
        )
        if not run.final_synthesis:
            return Response(
                {"detail": "O Conselho ainda não possui síntese final para exportação."},
                status=status.HTTP_409_CONFLICT,
            )
        approval = (
            StudioApproval.objects.filter(
                project=run.project,
                artifact=f"editorial_council:{run.id}",
            )
            .select_related("decided_by")
            .order_by("-id")
            .first()
        )
        try:
            content = render_council_export(run, approval, export_format)
        except (ValueError, RuntimeError):
            logger.exception(
                "Falha ao exportar Conselho Editorial %s em %s",
                run.pk,
                export_format,
            )
            return Response(
                {"detail": "Não foi possível gerar o relatório do Conselho Editorial."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = HttpResponse(content, content_type=COUNCIL_EXPORT_MIMES[export_format])
        response["Content-Disposition"] = (
            f'attachment; filename="{council_export_filename(run, export_format)}"'
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class StudioCouncilRunDetailView(generics.RetrieveAPIView):
    serializer_class = EditorialCouncilRunSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        return EditorialCouncilRun.objects.filter(project__created_by=self.request.user).prefetch_related("agent_runs")


class StudioCouncilDecisionView(APIView):
    permission_classes = [IsLocalStudioAdmin]
    decision = None

    def post(self, request, pk):
        raw_notes = request.data.get("notes", "")
        if not isinstance(raw_notes, str):
            return Response({"detail": "As observacoes devem ser texto."}, status=status.HTTP_400_BAD_REQUEST)
        if len(raw_notes) > 4000:
            return Response({"detail": "As observacoes excedem o limite de 4.000 caracteres."}, status=status.HTTP_400_BAD_REQUEST)
        notes = raw_notes.strip()
        with transaction.atomic():
            run = generics.get_object_or_404(
                EditorialCouncilRun.objects.select_for_update().select_related("project"),
                pk=pk, project__created_by=request.user,
            )
            current_plan = ModernizationPlan.objects.select_for_update().get(project=run.project)
            if current_plan.version != run.plan_version or current_plan.status != "approved":
                if run.status == "awaiting_human_approval":
                    run.status = "cancelled"
                    run.completed_at = timezone.now()
                    run.error_code = "plan_invalid"
                    run.save(update_fields=["status", "completed_at", "error_code", "updated_at"])
                return Response({"detail": "A execuÃ§Ã£o nÃ£o corresponde a um plano aprovado atual."}, status=status.HTTP_409_CONFLICT)
            if run.status != "awaiting_human_approval":
                return Response({"detail": "A execuÃ§Ã£o nÃ£o estÃ¡ aguardando decisÃ£o humana."}, status=status.HTTP_409_CONFLICT)
            run.status = self.decision
            run.save(update_fields=["status", "updated_at"])
            StudioApproval.objects.create(
                project=run.project, artifact=f"editorial_council:{run.id}",
                decision="approved" if self.decision == "approved" else "revision",
                notes=notes, decided_by=request.user,
            )
        return Response(EditorialCouncilRunSerializer(run).data)


class StudioCouncilApproveView(StudioCouncilDecisionView):
    decision = "approved"


class StudioCouncilRevisionView(StudioCouncilDecisionView):
    decision = "revision_requested"


class BookUploadView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        return Book.objects.select_related("trilha").all()


class StudioProviderListView(APIView):
    """Lista metadados seguros dos providers disponíveis para o Content Studio.

    Esta rota não realiza chamadas externas e nunca expõe credenciais.
    O suporte a structured output é declarado apenas para adapters já
    validados pelo fluxo de geração de plano.
    """

    permission_classes = [IsLocalStudioAdmin]

    def get(self, request):
        configured_default = canonical_provider_name(
            getattr(settings, "CONTENT_STUDIO_PROVIDER", "")
        )

        providers = []
        for provider_id, metadata in SENSEI_PROVIDER_CATALOG.items():
            canonical = canonical_provider_name(provider_id) or provider_id
            available = provider_is_available(canonical)
            plan_structured_output = canonical in PLAN_STRUCTURED_OUTPUT_PROVIDERS
            content_structured_output = canonical in CONTENT_STRUCTURED_OUTPUT_PROVIDERS
            structured_output = plan_structured_output or content_structured_output

            providers.append(
                {
                    "id": canonical,
                    "label": metadata["label"],
                    "model": get_provider_model(canonical),
                    "available": available,
                    "structured_output": structured_output,
                    "selectable_for_plan": available and plan_structured_output,
                    "selectable_for_content": available and content_structured_output,
                }
            )

        return Response(
            {
                "default_provider": configured_default,
                "providers": providers,
            },
            status=status.HTTP_200_OK,
        )


class StudioProviderCheckView(APIView):
    """Pré-validação local; não chama providers externos nem consome créditos."""

    permission_classes = [IsLocalStudioAdmin]

    def post(self, request):
        operation = request.data.get("operation", "generate_plan")
        if operation != "generate_plan":
            return Response(
                {
                    "detail": "Operação de preflight não suportada.",
                    "error_code": "unsupported_operation",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        project_id = request.data.get("project_id")
        if isinstance(project_id, bool):
            project_id = None
        try:
            project_id = int(project_id)
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": "Informe um project_id válido.",
                    "error_code": "invalid_project",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = generics.get_object_or_404(
            StudioProject,
            pk=project_id,
            created_by=request.user,
        )

        try:
            provider_name = _resolve_plan_provider(request.data.get("provider"))
        except StudioPlanProviderSelectionError as exc:
            return Response(
                {"detail": exc.detail, "error_code": exc.code},
                status=exc.status_code,
            )

        try:
            inputs = _prepare_plan_generation_inputs(project)
            prepared = prepare_modernization_plan_request(
                project,
                inputs["chunks"],
                grounded_context=inputs["grounded_context"],
                provider_name=provider_name,
            )
        except StudioResearchError as exc:
            return Response(
                {"detail": str(exc), "error_code": "research_context_invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "error_code": "plan_preflight_invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError:
            logger.exception(
                "Falha local no preflight do plano do projeto %s",
                project.pk,
            )
            return Response(
                {
                    "detail": "Não foi possível consultar as fontes locais do projeto.",
                    "error_code": "local_retrieval_unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        warnings = []
        if not prepared["has_grounded_sources"]:
            warnings.append(
                "A geração será um rascunho sem fontes verificadas e exigirá revisão humana."
            )

        return Response(
            {
                "operation": "generate_plan",
                "project_id": project.pk,
                "ready": True,
                "provider": _plan_provider_metadata(provider_name),
                "payload": {
                    "generation_mode": prepared["generation_mode"],
                    "context_source": prepared["context_source"],
                    "source_chunk_count": len(inputs["chunks"]),
                    "context_chars": prepared["context_chars"],
                    "prompt_chars": prepared["prompt_chars"],
                    "schema_chars": prepared["schema_chars"],
                    "total_chars": prepared["total_chars"],
                    "estimated_tokens": prepared["estimated_tokens"],
                    "estimate_note": prepared["estimate_note"],
                },
                "warnings": warnings,
            },
            status=status.HTTP_200_OK,
        )


class StudioStatusView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request):
        from django.conf import settings

        sources = LibrarySource.objects.all()
        active_sources = sources.exclude(status="missing")
        return Response({
            "enabled": settings.DDJ_CONTENT_STUDIO_ENABLED,
            "local_only": settings.DDJ_CONTENT_STUDIO_LOCAL_ONLY,
            "sources": active_sources.count(),
            "supported": active_sources.filter(status="supported").count(),
            "unsupported": active_sources.filter(status="unsupported").count(),
            "missing": sources.filter(status="missing").count(),
            "books": Book.objects.count(),
            "ready_books": Book.objects.filter(status="ready").count(),
            "scripts": GeneratedScript.objects.count(),
        })


class LibraryScanView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request):
        try:
            return Response(scan_library(), status=status.HTTP_200_OK)
        except (OSError, ValueError) as exc:
            logger.warning("Falha segura ao examinar o acervo: %s", type(exc).__name__)
            return Response({"detail": "NÃ£o foi possÃ­vel examinar o acervo configurado."}, status=status.HTTP_400_BAD_REQUEST)


class LibrarySourcePagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class LibrarySourceListView(generics.ListAPIView):
    serializer_class = LibrarySourceSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = LibrarySourcePagination

    def get_queryset(self):
        duplicate = LibrarySource.objects.filter(sha256=OuterRef("sha256")).exclude(pk=OuterRef("pk")).exclude(status="missing")
        queryset = LibrarySource.objects.select_related("book").annotate(
            _duplicate=Case(When(sha256="", then=Value(False)), default=Exists(duplicate), output_field=BooleanField())
        )
        status_filter = self.request.query_params.get("status")
        rag_status = self.request.query_params.get("rag_status")
        extension = self.request.query_params.get("extension")
        search = self.request.query_params.get("search", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.exclude(status="missing")
        if extension:
            queryset = queryset.filter(extension=extension.lstrip(".").lower())
        if search:
            queryset = queryset.filter(
                Q(relative_path__icontains=search)
                | Q(filename__icontains=search)
                | Q(book__title__icontains=search)
            )
        if rag_status == "not_processed":
            queryset = queryset.filter(book__isnull=True)
        elif rag_status in {"uploaded", "processing", "ready", "error"}:
            queryset = queryset.filter(book__status=rag_status)
        return queryset


class LibrarySourceProcessView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        from .services.book_storage import identity_lock, check_duplicate
        from .services.catalog import _sha256
        with identity_lock():
            source = generics.get_object_or_404(
                LibrarySource.objects.select_for_update().prefetch_related("book"), pk=pk
            )
            if source.status != "supported" or source.extension.lower() not in {"pdf", "epub", "docx", "txt"}:
                return Response(
                    {"detail": "Esta fonte não está disponível para processamento."},
                    status=status.HTTP_409_CONFLICT,
                )
            if source.sha256 and LibrarySource.objects.filter(sha256=source.sha256).exclude(pk=source.pk).exclude(status="missing").exists():
                return Response(
                    {"detail": "Fontes duplicadas não podem ser processadas."},
                    status=status.HTTP_409_CONFLICT,
                )

            book = getattr(source, "book", None)

            needs_file_copy = book is None
            if book is not None:
                try:
                    needs_file_copy = not book.file or not Path(book.file.path).is_file()
                except (OSError, ValueError):
                    needs_file_copy = True

            if needs_file_copy:
                try:
                    root = settings.LOCAL_LIBRARY_PATH.expanduser().resolve(strict=True)
                    candidate = (root / Path(source.relative_path)).resolve(strict=True)
                    candidate.relative_to(root)
                except (OSError, RuntimeError, ValueError):
                    return Response(
                        {"detail": "A fonte catalogada não está disponível."},
                        status=status.HTTP_409_CONFLICT,
                    )

                if not candidate.is_file():
                    return Response(
                        {"detail": "A fonte catalogada não está disponível."},
                        status=status.HTTP_409_CONFLICT,
                    )

                if book is None:
                    digest = _sha256(candidate)
                    check_duplicate(digest)
                    book = Book(title=Path(source.filename).stem[:255], source=source, sha256=digest)

                with candidate.open("rb") as stream:
                    book.file.save(Path(source.filename).name, File(stream), save=False)

                if book.pk is None:
                    book.save()
                else:
                    book.save(update_fields=["file"])

            status_url = request.build_absolute_uri(f"/api/library/books/{book.id}/status/")
            if book.status in {"processing", "ready"}:
                return Response(
                    {
                        "source_id": source.id,
                        "book_id": book.id,
                        "status": book.status,
                        "status_url": status_url,
                    },
                    status=status.HTTP_200_OK,
                )

            previous_state = {
                "status": book.status,
                "error_message": book.error_message,
                "processed_at": book.processed_at,
                "progress_percent": book.progress_percent,
                "progress_stage": book.progress_stage,
            }
            book.status = "processing"
            book.error_message = ""
            book.progress_percent = 0
            book.progress_stage = ""
            book.save(
                update_fields=[
                    "status",
                    "error_message",
                    "progress_percent",
                    "progress_stage",
                ]
            )

            queued = {"task_id": None, "error": None}

            def enqueue_processing():
                try:
                    queued["task_id"] = process_book.delay(book.id).id
                except Exception as exc:
                    logger.exception(
                        "Falha ao enfileirar processamento do livro %s",
                        book.id,
                    )
                    queued["error"] = exc
                    Book.objects.filter(
                        pk=book.id,
                        status="processing",
                        progress_percent=0,
                        progress_stage="",
                    ).update(**previous_state)

            transaction.on_commit(enqueue_processing)

        if queued["error"] is not None:
            return Response(
                {"detail": "Não foi possível acessar a fila de processamento."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "source_id": source.id,
                "book_id": book.id,
                "task_id": queued["task_id"],
                "status": "processing",
                "status_url": status_url,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class StudioProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = StudioProjectSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        archived = self.request.query_params.get("archived", "false").lower() == "true"
        return StudioProject.objects.filter(created_by=self.request.user, is_archived=archived).select_related("research_context", "formation_link").prefetch_related("books", "citations", "approvals", "editorial_comments", "artifacts", "research_context__evidence")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class StudioProjectDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = StudioProjectSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        return StudioProject.objects.filter(created_by=self.request.user).select_related("research_context", "formation_link").prefetch_related("books", "citations", "approvals", "editorial_comments", "artifacts", "research_context__evidence")


def _record_plan_version(project, plan, user, origin):
    return EditorialPlanVersion.objects.get_or_create(
        project=project,
        version=plan.version,
        defaults={
            "content": plan.proposed_architecture,
            "project_type": project.project_type,
            "origin": origin,
            "state": plan.status,
            "created_by": user,
        },
    )[0]


class StudioGeneratePlanView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        project = generics.get_object_or_404(
            StudioProject,
            pk=pk,
            created_by=request.user,
        )

        try:
            provider_name = _resolve_plan_provider(request.data.get("provider"))
        except StudioPlanProviderSelectionError as exc:
            return Response(
                {"detail": exc.detail, "error_code": exc.code},
                status=exc.status_code,
            )

        try:
            inputs = _prepare_plan_generation_inputs(project)
        except StudioResearchError as exc:
            return Response(
                {"detail": str(exc), "error_code": "research_context_invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "error_code": "plan_preparation_invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError:
            logger.exception(
                "Falha local ao preparar fontes do plano do projeto %s",
                project.pk,
            )
            return Response(
                {
                    "detail": "Não foi possível consultar as fontes locais do projeto.",
                    "error_code": "local_retrieval_unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        approved_context = inputs["approved_context"]
        chunks = inputs["chunks"]
        grounded_context = inputs["grounded_context"]

        with transaction.atomic():
            project = StudioProject.objects.select_for_update().get(pk=project.pk)
            existing_plan = ModernizationPlan.objects.filter(project=project).first()
            expected_version = existing_plan.version if existing_plan else 0
            previous_plan = existing_plan.proposed_architecture if existing_plan else None
            project.status = "planning"
            project.save(update_fields=["status", "updated_at"])

        try:
            data, raw = generate_modernization_plan(
                project,
                chunks,
                previous_plan,
                grounded_context,
                provider_name=provider_name,
            )

            data["proposed_architecture"].pop("dossier_provenance", None)
            if approved_context:
                data["proposed_architecture"]["dossier_provenance"] = {
                    "id": approved_context["dossier_version_id"],
                    "version": approved_context["dossier_version"],
                    "research_policy": approved_context["research_policy"],
                    "documentary_grounding": approved_context["documentary_grounding"],
                }

        except AIProviderError as exc:
            logger.warning(
                "studio_plan_provider_failed project_id=%s provider=%s error_code=%s",
                project.pk,
                getattr(exc, "provider", provider_name),
                getattr(exc, "code", "unknown"),
            )
            _restore_project_after_plan_failure(project.pk, expected_version)

            error_code = getattr(exc, "code", "unknown")
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            if error_code == "payload_too_large":
                response_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            elif error_code == "rate_limit":
                response_status = status.HTTP_429_TOO_MANY_REQUESTS

            return Response(
                {
                    "detail": str(exc),
                    "provider": canonical_provider_name(
                        getattr(exc, "provider", provider_name)
                    ) or provider_name,
                    "error_code": error_code,
                },
                status=response_status,
            )

        except (RuntimeError, ValueError, StudioResearchError) as exc:
            logger.exception(
                "Falha ao gerar plano editorial do projeto %s [%s]: %s",
                project.pk,
                type(exc).__name__,
                str(exc),
            )
            _restore_project_after_plan_failure(project.pk, expected_version)
            return Response(
                {
                    "detail": (
                        "Não foi possível gerar o plano editorial. "
                        "Consulte o log do servidor para identificar a causa técnica."
                    ),
                    "provider": provider_name,
                    "error_code": "generation_failed",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            locked_project = StudioProject.objects.select_for_update().get(pk=project.pk)
            previous = (
                ModernizationPlan.objects.select_for_update()
                .filter(project=locked_project)
                .first()
            )
            current_version = previous.version if previous else 0
            if current_version != expected_version:
                return Response(
                    {
                        "detail": "O plano mudou durante a geração; gere novamente.",
                        "error_code": "plan_version_conflict",
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if previous:
                _record_plan_version(
                    locked_project,
                    previous,
                    request.user,
                    "revision",
                )

            version = (previous.version + 1) if previous else 1
            plan, _ = ModernizationPlan.objects.update_or_create(
                project=locked_project,
                defaults={
                    **data,
                    "raw_response": raw,
                    "status": "review",
                    "version": version,
                },
            )
            _record_plan_version(locked_project, plan, request.user, "ai")

            locked_project.citations.filter(
                purpose="modernization_plan"
            ).delete()
            SourceCitation.objects.bulk_create(
                [
                    SourceCitation(
                        project=locked_project,
                        chunk=chunk,
                        book_title=chunk.book.title,
                        page_number=chunk.page_number,
                        excerpt=chunk.content[:1500],
                    )
                    for chunk in chunks
                ]
            )

            locked_project.status = "awaiting_approval"
            locked_project.save(update_fields=["status", "updated_at"])
            project = locked_project

        return Response(StudioProjectSerializer(project).data)


class StudioPlanEditView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def put(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        current = generics.get_object_or_404(ModernizationPlan, project=project)
        serializer = EditorialPlanEditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        edited = serializer.validated_data["plan"]
        edited.pop("contract_version", None)
        try:
            validate_editorial_plan(project.project_type, edited)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        edited["contract_version"] = "editorial-plan-v1"
        with transaction.atomic():
            project = StudioProject.objects.select_for_update().get(pk=project.pk)
            current = ModernizationPlan.objects.select_for_update().get(pk=current.pk, project=project)
            edited.pop("dossier_provenance", None)
            if "dossier_provenance" in current.proposed_architecture:
                edited["dossier_provenance"] = current.proposed_architecture["dossier_provenance"]
            _record_plan_version(project, current, request.user, "revision")
            current.version += 1
            current.proposed_architecture = edited
            current.status = "review"
            current.save(update_fields=["version", "proposed_architecture", "status", "updated_at"])
            _record_plan_version(project, current, request.user, "human_edit")
            project.status = "awaiting_approval"
            project.save(update_fields=["status", "updated_at"])
        return Response(StudioProjectSerializer(project).data)


class StudioPlanVersionListView(generics.ListAPIView):
    serializer_class = EditorialPlanVersionSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_queryset(self):
        project = generics.get_object_or_404(StudioProject, pk=self.kwargs["pk"], created_by=self.request.user)
        return project.plan_versions.select_related("created_by")


class StudioCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = EditorialCommentSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_project(self):
        return generics.get_object_or_404(StudioProject, pk=self.kwargs["pk"], created_by=self.request.user)

    def get_queryset(self):
        return self.get_project().editorial_comments.select_related("author")

    def perform_create(self, serializer):
        project = self.get_project()
        target_type = serializer.validated_data.get("target_type", "plan")
        target_id = serializer.validated_data.get("target_id", "")
        plan = getattr(project, "modernization_plan", None)
        plan_data = plan.proposed_architecture if plan else {}
        valid_ids = {
            "module": {str(item.get("editorial_id")) for item in plan_data.get("modules", []) if item.get("editorial_id")},
            "lesson": {str(item.get("editorial_id")) for module in plan_data.get("modules", []) for item in module.get("lessons", []) if item.get("editorial_id")},
            "video": {str(item.get("editorial_id")) for item in plan_data.get("videos", []) if item.get("editorial_id")},
            "section": set(plan_data.keys()),
        }
        if target_type in valid_ids and target_id not in valid_ids[target_type]:
            raise serializers.ValidationError({"target_id": "O alvo editorial nÃ£o pertence ao plano atual."})
        plan_version = plan.version if plan and target_type not in {"plan", "project"} else None
        serializer.save(
            project=project,
            author=self.request.user,
            target=f"{target_type}:{target_id}" if target_id else target_type,
            plan_version=plan_version,
        )


class StudioCommentResolveView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk, comment_pk):
        comment = generics.get_object_or_404(
            EditorialComment, pk=comment_pk, project_id=pk, project__created_by=request.user
        )
        comment.resolved = True
        comment.resolved_at = timezone.now()
        comment.save(update_fields=["resolved", "resolved_at"])
        return Response(EditorialCommentSerializer(comment).data)


class StudioArchiveView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        archived = bool(request.data.get("archived", True))
        project.is_archived = archived
        project.archived_at = timezone.now() if archived else None
        project.save(update_fields=["is_archived", "archived_at", "updated_at"])
        return Response(StudioProjectSerializer(project).data)


class StudioPermanentDeleteView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def delete(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user, is_archived=True)
        if request.data.get("confirmation") != "EXCLUIR DEFINITIVAMENTE":
            return Response({"detail": "ConfirmaÃ§Ã£o explÃ­cita obrigatÃ³ria."}, status=status.HTTP_400_BAD_REQUEST)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudioApprovalView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        if not hasattr(project, "modernization_plan"):
            return Response({"detail": "O projeto ainda não possui plano de modernização."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ApprovalInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        with transaction.atomic():
            StudioApproval.objects.create(project=project, artifact="modernization_plan", decision=decision, notes=serializer.validated_data.get("notes", ""), decided_by=request.user)
            project.modernization_plan.status = "approved" if decision == "approved" else "draft"
            project.modernization_plan.save(update_fields=["status", "updated_at"])
            EditorialPlanVersion.objects.filter(
                project=project, version=project.modernization_plan.version
            ).update(state=project.modernization_plan.status)
            project.status = "approved" if decision == "approved" else "planning"
            project.save(update_fields=["status", "updated_at"])
        return Response(StudioProjectSerializer(project).data)


class StudioGenerateContentView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        if not hasattr(project, "modernization_plan") or project.modernization_plan.status != "approved":
            return Response({"detail": "Aprove o plano de modernização antes de gerar conteúdo."}, status=status.HTTP_409_CONFLICT)
        serializer = ContentGenerationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_type = serializer.validated_data["target_type"]
        target_index = serializer.validated_data["target_index"]

        try:
            provider_name = _resolve_content_provider(request.data.get("provider"))
        except StudioContentProviderSelectionError as exc:
            return Response(
                {"detail": exc.detail, "error_code": exc.code},
                status=exc.status_code,
            )

        plan_data = project.modernization_plan.proposed_architecture
        semantic_project_type = normalize_project_type(project.project_type)
        if semantic_project_type == "content":
            collection = plan_data.get("videos", [])
            if target_type != "video":
                return Response({"detail": "Projetos de conteúdo geram um item de conteúdo por vez."}, status=status.HTTP_400_BAD_REQUEST)
        elif target_type == "module":
            collection = plan_data.get("modules", [])
        elif target_type == "lesson":
            collection = [lesson for module in plan_data.get("modules", []) for lesson in module.get("lessons", [])]
        else:
            return Response({"detail": "SeleÃ§Ã£o incompatÃ­vel com o tipo editorial."}, status=status.HTTP_400_BAD_REQUEST)
        if target_index >= len(collection):
            return Response({"detail": "Item editorial selecionado nÃ£o existe."}, status=status.HTTP_400_BAD_REQUEST)
        plan_version = project.modernization_plan.version
        target = collection[target_index]
        target_id = target.get("editorial_id") or f"legacy-v{plan_version}:{target_type}:{target_index}"
        try:
            content, raw = generate_content_item(
                project,
                project.modernization_plan,
                target_type,
                target_index,
                target,
                provider_name=provider_name,
            )
        except AIProviderError as exc:
            logger.warning(
                "studio_content_generation_provider_failed project_id=%s target_type=%s "
                "target_index=%s provider=%s error_code=%s",
                project.pk,
                target_type,
                target_index,
                getattr(exc, "provider", provider_name),
                getattr(exc, "code", "unknown"),
            )
            error_code = getattr(exc, "code", "unknown")
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            if error_code == "payload_too_large":
                response_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            elif error_code == "rate_limit":
                response_status = status.HTTP_429_TOO_MANY_REQUESTS

            return Response(
                {
                    "detail": str(exc),
                    "provider": canonical_provider_name(
                        getattr(exc, "provider", provider_name)
                    ) or provider_name,
                    "error_code": error_code,
                },
                status=response_status,
            )
        except (RuntimeError, ValueError) as exc:
            logger.warning(
                "studio_content_generation_failed project_id=%s target_type=%s "
                "target_index=%s category=%s",
                project.pk,
                target_type,
                target_index,
                type(exc).__name__,
            )
            return Response(
                {"detail": "Não foi possível gerar o pacote de conteúdo."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        with transaction.atomic():
            project = StudioProject.objects.select_for_update().get(pk=project.pk)
            current_plan = ModernizationPlan.objects.select_for_update().get(project=project)
            if current_plan.version != plan_version or current_plan.status != "approved":
                return Response({"detail": "O plano mudou durante a geraÃ§Ã£o; gere o item novamente."}, status=status.HTTP_409_CONFLICT)
            package, _ = ContentPackage.objects.select_for_update().get_or_create(project=project)
            items = list(package.generated_items)
            generation = 1 + max((item.get("generation", 0) for item in items if item.get("target_id") == target_id), default=0)
            items.append({
                "id": str(uuid4()),
                "target_type": target_type,
                "target_id": target_id,
                "target_index": target_index,
                "plan_version": plan_version,
                "generation": generation,
                "status": "draft",
                "provider": provider_name,
                "model": get_provider_model(provider_name),
                "content": content,
                "created_at": timezone.now().isoformat(),
            })
            package.generated_items = items
            package.raw_response = raw
            package.publication_status = "draft"
            package.save(update_fields=["generated_items", "raw_response", "publication_status", "updated_at"])
            project.status = "content"
            project.save(update_fields=["status", "updated_at"])
            artifact = StudioArtifact.objects.create(
                project=project, artifact_type="YOUTUBE_PACKAGE" if semantic_project_type == "content" else "PREMIUM_CONTENT",
                target_type=target_type, target_id=target_id, plan_version=plan_version, generation=generation,
                content=content, created_by=request.user,
            )
            link = getattr(project, "formation_link", None)
            if semantic_project_type == "formation" and link and link.synced_plan_version == plan_version:
                artifact.linked_formation = link.formation
                if target_type == "lesson":
                    unit_id = (link.identity_map or {}).get("units", {}).get(target_id)
                    artifact.linked_unit = SenseiStudyUnit.objects.filter(pk=unit_id, module__formation=link.formation).first()
                artifact.save(update_fields=["linked_formation", "linked_unit"])
        return Response({"package": ContentPackageSerializer(package).data, "artifact": StudioArtifactSerializer(artifact).data})


class StudioDossierView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        return Response(StudioDossierSerializer(project.dossier_versions.all(), many=True).data)

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        serializer = StudioDossierInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = create_dossier_version(project_id=project.pk, actor=request.user, **serializer.validated_data)
        except DjangoValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StudioDossierSerializer(version).data, status=status.HTTP_201_CREATED)


class StudioDossierTransitionView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk, version_pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        serializer = StudioDossierTransitionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            version = transition_dossier_version(project_id=project.pk, actor=request.user, version_id=version_pk, **serializer.validated_data)
        except DjangoValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(StudioDossierSerializer(version).data)


class StudioResearchView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        try:
            preparation = prepare_dossier_from_research(project_id=project.pk, actor=request.user)
        except DjangoValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        data = dict(StudioResearchContextSerializer(project.research_context).data)
        data["dossier_preparation"] = preparation
        return Response(data)

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        try:
            context = build_research_context(project, dossier_builder=generate_grounded_dossier)
        except (StudioResearchError, RuntimeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(StudioResearchContextSerializer(context).data, status=status.HTTP_201_CREATED)


class StudioPlanExportView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk, export_format):
        project = generics.get_object_or_404(
            StudioProject.objects.select_related("modernization_plan", "research_context")
            .prefetch_related("citations", "research_context__evidence"),
            pk=pk,
            created_by=request.user,
        )
        if export_format not in PLAN_EXPORT_MIMES:
            return Response(
                {"detail": "Formato de exportação não suportado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        plan = getattr(project, "modernization_plan", None)
        if plan is None:
            return Response(
                {"detail": "Gere o plano editorial antes de exportar."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            content = render_plan_export(project, plan, export_format)
        except (ValueError, RuntimeError):
            logger.exception(
                "Falha ao exportar plano editorial do projeto %s em %s",
                project.pk,
                export_format,
            )
            return Response(
                {"detail": "Não foi possível gerar a exportação do plano editorial."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = HttpResponse(content, content_type=PLAN_EXPORT_MIMES[export_format])
        response["Content-Disposition"] = f'attachment; filename="{plan_export_filename(project, export_format)}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class StudioSectionExportView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk, section, export_format):
        if export_format not in SECTION_EXPORT_MIMES:
            return Response(
                {"detail": "Formato de exportação não suportado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        project = generics.get_object_or_404(
            StudioProject.objects.select_related(
                "modernization_plan",
                "research_context",
                "content_package",
            ).prefetch_related(
                "research_context__evidence",
                "dossier_versions",
                "artifacts",
                "council_runs__agent_runs",
            ),
            pk=pk,
            created_by=request.user,
        )

        try:
            payload = render_section_export(project, section, export_format)
            filename = section_export_filename(project, section, export_format)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except (RuntimeError, TypeError):
            logger.exception(
                "Falha ao exportar seção do Content Studio project_id=%s section=%s format=%s",
                project.pk,
                section,
                export_format,
            )
            return Response(
                {"detail": "Não foi possível exportar esta seção do Content Studio."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response = HttpResponse(payload, content_type=SECTION_EXPORT_MIMES[export_format])
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class StudioArtifactTransitionView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        artifact = generics.get_object_or_404(StudioArtifact, pk=pk, project__created_by=request.user)
        serializer = StudioArtifactTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_status = serializer.validated_data["status"]
        allowed = {"DRAFT": {"REVIEW"}, "REVIEW": {"DRAFT", "APPROVED"}, "APPROVED": {"REVIEW"}}
        if next_status != artifact.status and next_status not in allowed[artifact.status]:
            return Response({"detail": "Transição editorial não permitida."}, status=status.HTTP_400_BAD_REQUEST)
        artifact.status = next_status
        artifact.reviewed_by = request.user if next_status == "APPROVED" else None
        artifact.reviewed_at = timezone.now() if next_status == "APPROVED" else None
        artifact.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(StudioArtifactSerializer(artifact).data)


class StudioArtifactLinkView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        artifact = generics.get_object_or_404(StudioArtifact, pk=pk, project__created_by=request.user)
        serializer = StudioArtifactLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        formation_id = serializer.validated_data.get("formation_id")
        unit_id = serializer.validated_data.get("unit_id")
        formation = generics.get_object_or_404(_visible_formations(request.user), pk=formation_id) if formation_id else None
        unit = _visible_unit(request.user, unit_id) if unit_id else None
        if unit and formation and unit.module.formation_id != formation.id:
            return Response({"detail": "A unidade não pertence à formação selecionada."}, status=status.HTTP_400_BAD_REQUEST)
        artifact.linked_unit = unit
        artifact.linked_formation = formation or (unit.module.formation if unit else None)
        artifact.save(update_fields=["linked_unit", "linked_formation", "updated_at"])
        return Response(StudioArtifactSerializer(artifact).data)


class StudioArtifactExportView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk, export_format):
        artifact = generics.get_object_or_404(StudioArtifact, pk=pk, project__created_by=request.user)
        if artifact.status not in {"REVIEW", "APPROVED"}:
            return Response({"detail": "Envie o artefato para revisão antes de exportar."}, status=status.HTTP_409_CONFLICT)
        renderers = {"docx": (render_artifact_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                     "html": (render_artifact_html, "text/html; charset=utf-8"),
                     "teleprompter": (lambda item: render_artifact_html(item, teleprompter=True), "text/html; charset=utf-8")}
        if export_format not in renderers:
            return Response({"detail": "Formato de exportação não suportado."}, status=status.HTTP_404_NOT_FOUND)
        renderer, content_type = renderers[export_format]
        extension = "html" if export_format == "teleprompter" else export_format
        try:
            payload = renderer(artifact)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        response = HttpResponse(payload, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{artifact_filename(artifact, extension)}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class StudioMaterializeFormationView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject.objects.select_related("modernization_plan"), pk=pk, created_by=request.user)
        try:
            link, changed = materialize_premium_formation(project, request.user)
        except StudioFormationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"formation_id": link.formation_id, "synced_plan_version": link.synced_plan_version, "changed": changed})


class BookProcessView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        with transaction.atomic():
            book = generics.get_object_or_404(Book.objects.select_for_update(), pk=pk)
            if book.lifecycle != "active" or book.duplicate_of_id:
                return Response({"detail": "Restaure o livro ou processe o registro original."}, status=409)
            if book.status == "processing":
                return Response({"detail": "Livro já está sendo processado."}, status=status.HTTP_409_CONFLICT)
            previous_state = {
                "status": book.status,
                "error_message": book.error_message,
                "processed_at": book.processed_at,
                "progress_percent": book.progress_percent,
                "progress_stage": book.progress_stage,
            }
            book.status = "processing"
            book.error_message = ""
            book.processed_at = None
            book.progress_percent = 0
            book.progress_stage = ""
            book.save(update_fields=["status", "error_message", "processed_at", "progress_percent", "progress_stage"])

            queued = {"task_id": None, "error": None}

            def enqueue_processing():
                try:
                    queued["task_id"] = process_book.delay(book.id).id
                except Exception as exc:
                    logger.exception("Falha ao enfileirar processamento do livro %s", book.id)
                    queued["error"] = exc
                    Book.objects.filter(
                        pk=book.id,
                        status="processing",
                        progress_percent=0,
                        progress_stage="",
                    ).update(**previous_state)

            transaction.on_commit(enqueue_processing)

        if queued["error"] is not None:
            return Response(
                {"detail": "Não foi possível acessar a fila de processamento."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"book_id": book.id, "task_id": queued["task_id"], "status": "queued"}, status=status.HTTP_202_ACCEPTED)


class BookStatusView(generics.RetrieveAPIView):
    queryset = Book.objects.all()
    serializer_class = BookStatusSerializer
    permission_classes = [IsLocalStudioAdmin]


class TrilhaListView(generics.ListAPIView):
    queryset = Trilha.objects.all()
    serializer_class = TrilhaSerializer
    permission_classes = [IsLocalStudioAdmin]


class ScriptGenerateView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request):
        serializer = GenerateScriptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trilha = serializer.validated_data["trilha"]
        books = serializer.validated_data["books"]
        tema = serializer.validated_data["tema"]
        try:
            chunks = buscar_chunks_relevantes(tema, [book.id for book in books])
        except RuntimeError as exc:
            return Response(
                {"detail": "Não foi possível consultar as fontes selecionadas."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not chunks:
            return Response({"detail": "Nenhum trecho relevante foi encontrado."}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        try:
            data, raw = gerar_roteiro(tema, trilha, chunks)
        except (RuntimeError, ValueError) as exc:
            return Response(
                {"detail": "Não foi possível gerar o roteiro."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        with transaction.atomic():
            script = GeneratedScript.objects.create(
                trilha=trilha,
                titulo_video=str(data["titulo_video"])[:255],
                problema_resolvido=data["problema_resolvido"],
                ganho_negocio=data["ganho_negocio"],
                estrutura=data["estrutura"],
                conteudo_bruto=raw,
                created_by=request.user,
            )
            script.books.set(books)
        return Response(GeneratedScriptSerializer(script).data, status=status.HTTP_201_CREATED)


class ScriptListView(generics.ListAPIView):
    serializer_class = GeneratedScriptSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        queryset = GeneratedScript.objects.select_related("trilha", "created_by").prefetch_related("books")
        return queryset if self.request.user.is_staff else queryset.filter(created_by=self.request.user)


class ScriptDetailView(generics.RetrieveAPIView):
    serializer_class = GeneratedScriptSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        queryset = GeneratedScript.objects.select_related("trilha", "created_by").prefetch_related("books")
        return queryset if self.request.user.is_staff else queryset.filter(created_by=self.request.user)


def _visible_formations(user):
    return SenseiFormation.objects.filter(Q(created_by=user) | Q(created_by__isnull=True))


def _refresh_sensei_progress(formation, user):
    progress, _ = SenseiProgress.objects.get_or_create(formation=formation, user=user)
    competency_ids = formation.competencies.values_list("id", flat=True)
    total = competency_ids.count()
    demonstrated = SenseiCompetencyProgress.objects.filter(
        competency_id__in=competency_ids,
        user=user,
        state__in=(SenseiCompetencyProgress.State.DEMONSTRATED, SenseiCompetencyProgress.State.TEACHING_READY),
    ).count()
    active = SenseiCompetencyProgress.objects.filter(competency_id__in=competency_ids, user=user).exclude(state=SenseiCompetencyProgress.State.NOT_STARTED).exists()
    percentage = round((demonstrated / total) * 100, 2) if total else 0
    state = SenseiProgress.State.COMPLETED if total and demonstrated == total else (SenseiProgress.State.IN_PROGRESS if active else SenseiProgress.State.NOT_STARTED)
    update_fields = []
    if progress.percentage != percentage:
        progress.percentage = percentage; update_fields.append("percentage")
    if progress.state != state:
        progress.state = state; update_fields.append("state")
    if state != SenseiProgress.State.NOT_STARTED and progress.started_at is None:
        progress.started_at = timezone.now(); update_fields.append("started_at")
    completed_at = timezone.now() if state == SenseiProgress.State.COMPLETED and progress.completed_at is None else (None if state != SenseiProgress.State.COMPLETED else progress.completed_at)
    if progress.completed_at != completed_at:
        progress.completed_at = completed_at; update_fields.append("completed_at")
    if update_fields:
        progress.save(update_fields=[*update_fields, "updated_at"])
    return progress


class SenseiFormationListCreateView(generics.ListCreateAPIView):
    serializer_class = SenseiFormationSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_queryset(self):
        return _visible_formations(self.request.user).prefetch_related("modules", "competencies", "progress_records")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SenseiFormationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = SenseiFormationSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        return _visible_formations(self.request.user).prefetch_related("modules", "competencies", "progress_records")


class SenseiFormationModuleListCreateView(generics.ListCreateAPIView):
    serializer_class = SenseiFormationModuleSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_formation(self):
        return generics.get_object_or_404(_visible_formations(self.request.user), pk=self.kwargs["formation_pk"])

    def get_queryset(self):
        return self.get_formation().modules.prefetch_related("study_units")

    def perform_create(self, serializer):
        serializer.save(formation=self.get_formation())


class SenseiStudyUnitListCreateView(generics.ListCreateAPIView):
    serializer_class = SenseiStudyUnitSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_module(self):
        return generics.get_object_or_404(
            SenseiFormationModule.objects.filter(Q(formation__created_by=self.request.user) | Q(formation__created_by__isnull=True)),
            pk=self.kwargs["module_pk"],
        )

    def get_queryset(self):
        return self.get_module().study_units.prefetch_related("sources")

    def perform_create(self, serializer):
        serializer.save(module=self.get_module())


class SenseiCompetencyListCreateView(generics.ListCreateAPIView):
    serializer_class = SenseiCompetencySerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_formation(self):
        return generics.get_object_or_404(_visible_formations(self.request.user), pk=self.kwargs["formation_pk"])

    def get_queryset(self):
        return self.get_formation().competencies.select_related("module")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "formation": self.get_formation()}

    def perform_create(self, serializer):
        serializer.save(formation=self.get_formation())


class SenseiEvidenceListCreateView(generics.ListCreateAPIView):
    serializer_class = SenseiCompetencyEvidenceSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_competency(self):
        return generics.get_object_or_404(
            SenseiCompetency.objects.filter(Q(formation__created_by=self.request.user) | Q(formation__created_by__isnull=True)),
            pk=self.kwargs["competency_pk"],
        )

    def get_queryset(self):
        return self.get_competency().evidences.filter(submitted_by=self.request.user).select_related("validated_by")

    def perform_create(self, serializer):
        serializer.save(competency=self.get_competency(), submitted_by=self.request.user)


class SenseiEvidenceReviewView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def patch(self, request, pk):
        evidence = generics.get_object_or_404(
            SenseiCompetencyEvidence.objects.select_related("competency__formation"),
            pk=pk, submitted_by=request.user,
        )
        if evidence.competency.formation.created_by_id not in (None, request.user.id):
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = SenseiEvidenceReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence.validation_status = serializer.validated_data["validation_status"]
        evidence.feedback = serializer.validated_data.get("feedback", "")
        evidence.validated_by = request.user
        evidence.validated_at = timezone.now()
        evidence.save(update_fields=["validation_status", "feedback", "validated_by", "validated_at", "updated_at"])
        return Response(SenseiCompetencyEvidenceSerializer(evidence).data)


class SenseiFormationProgressView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, formation_pk):
        formation = generics.get_object_or_404(_visible_formations(request.user), pk=formation_pk)
        return Response(SenseiProgressSerializer(_refresh_sensei_progress(formation, request.user)).data)


class SenseiLearningProviderView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get_formation(self, request, formation_pk):
        return generics.get_object_or_404(_visible_formations(request.user), pk=formation_pk)

    def get(self, request, formation_pk):
        formation = self.get_formation(request, formation_pk)
        selected_provider = None
        selection_source = None
        try:
            selected_provider, _, selection_source = resolve_provider(request.user, formation)
        except SenseiLearningError:
            pass
        return Response({
            "providers": available_providers(),
            "selected_provider": selected_provider,
            "selection_source": selection_source,
        })

    def put(self, request, formation_pk):
        formation = self.get_formation(request, formation_pk)
        serializer = SenseiLearningProviderPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = canonical_provider_name(serializer.validated_data["provider"])
        if not provider or not provider_is_available(provider):
            return Response({"detail": "O provider informado não está disponível para esta formação."}, status=status.HTTP_400_BAD_REQUEST)
        preference, _ = SenseiLearningProviderPreference.objects.update_or_create(
            user=request.user, formation=formation, defaults={"provider": provider},
        )
        return Response({"provider": preference.provider})


class SenseiCompetencyProgressView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get_competency(self, request, pk):
        return generics.get_object_or_404(
            SenseiCompetency.objects.filter(Q(formation__created_by=request.user) | Q(formation__created_by__isnull=True)), pk=pk
        )

    def get(self, request, pk):
        competency = self.get_competency(request, pk)
        progress, _ = SenseiCompetencyProgress.objects.get_or_create(competency=competency, user=request.user)
        return Response(SenseiCompetencyProgressSerializer(progress).data)

    def patch(self, request, pk):
        competency = self.get_competency(request, pk)
        progress, _ = SenseiCompetencyProgress.objects.get_or_create(competency=competency, user=request.user)
        serializer = SenseiCompetencyProgressSerializer(progress, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _refresh_sensei_progress(competency.formation, request.user)
        return Response(serializer.data)


def _visible_unit(user, pk):
    return generics.get_object_or_404(
        SenseiStudyUnit.objects.select_related("module__formation").filter(
            Q(module__formation__created_by=user) | Q(module__formation__created_by__isnull=True)
        ), pk=pk,
    )


class SenseiUnitStudyPlanView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        unit = _visible_unit(request.user, pk)
        plan = generics.get_object_or_404(
            SenseiUnitStudyPlan.objects.prefetch_related("prerequisites", "related_competencies", "unit__curated_sources", "unit__study_notes", "unit__study_progress_records"),
            unit=unit,
        )
        return Response(SenseiUnitStudyPlanSerializer(plan, context={"request": request}).data)

    def patch(self, request, pk):
        unit = _visible_unit(request.user, pk)
        plan = generics.get_object_or_404(SenseiUnitStudyPlan, unit=unit)
        serializer = SenseiUnitStudyPlanSerializer(plan, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SenseiDidacticLessonView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get_unit(self, request, pk):
        return _visible_unit(request.user, pk)

    def get_lesson(self, unit):
        content_type = ContentType.objects.get_for_model(unit)
        return DidacticLesson.objects.prefetch_related("sections", "sources").filter(
            learning_target_type=content_type, learning_target_id=unit.id, audience=DidacticLesson.Audience.SENSEI,
        ).first()

    def get(self, request, pk):
        lesson = self.get_lesson(self.get_unit(request, pk))
        return Response({"lesson": DidacticLessonSerializer(lesson).data if lesson else None})

    def post(self, request, pk):
        unit = self.get_unit(request, pk)
        try:
            lesson, created = generate_didactic_lesson(unit, request.user)
        except DidacticContentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except (AIProviderError, RuntimeError):
            logger.warning("Falha segura ao gerar aula didática do Sensei", exc_info=True)
            return Response({"detail": "Não foi possível gerar a aula neste momento."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(DidacticLessonSerializer(lesson).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @transaction.atomic
    def patch(self, request, pk):
        unit = self.get_unit(request, pk)
        lesson = generics.get_object_or_404(DidacticLesson.objects.select_for_update(), learning_target_type=ContentType.objects.get_for_model(unit), learning_target_id=unit.id, audience=DidacticLesson.Audience.SENSEI)
        serializer = DidacticLessonUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_status = serializer.validated_data.get("status")
        allowed = {"DRAFT": {"REVIEW", "ARCHIVED"}, "REVIEW": {"DRAFT", "APPROVED", "ARCHIVED"}, "APPROVED": {"REVIEW", "PUBLISHED", "ARCHIVED"}, "PUBLISHED": {"ARCHIVED"}, "ARCHIVED": {"DRAFT"}}
        if next_status and next_status != lesson.status and next_status not in allowed.get(lesson.status, set()):
            return Response({"detail": "Transição de status não permitida."}, status=status.HTTP_400_BAD_REQUEST)
        if (
            next_status == DidacticLesson.Status.REVIEW
            and lesson.source_mode == DidacticLesson.SourceMode.APPROVED_SOURCES
            and lesson.sources.exists()
            and not (lesson.grounding_snapshot or {}).get("sources")
        ):
            return Response(
                {"detail": "A aula não possui snapshot de grounding auditável. Regenere o rascunho com as fontes aprovadas atuais antes de enviar para revisão."},
                status=status.HTTP_409_CONFLICT,
            )
        snapshot = lesson.grounding_snapshot or {}
        has_ai_provenance = bool(lesson.ai_provider or lesson.ai_model or lesson.generated_at or snapshot.get("provider") or snapshot.get("model"))
        if (
            next_status in {DidacticLesson.Status.REVIEW, DidacticLesson.Status.APPROVED}
            and lesson.source_mode == DidacticLesson.SourceMode.APPROVED_SOURCES
            and has_ai_provenance
            and not has_editorial_claim_state(lesson)
        ):
            return Response(
                {"detail": "CLAIM_GROUNDING_REQUIRED: a aula não possui estado válido de grounding por afirmação em todas as seções. Regenere o rascunho com Claim-Level Grounding atual antes de enviar para revisão ou aprovar."},
                status=status.HTTP_409_CONFLICT,
            )
        update_human_lesson(lesson, request.user, serializer.validated_data)
        return Response(DidacticLessonSerializer(lesson).data)


class SenseiDidacticLessonExportView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk, export_format):
        unit = _visible_unit(request.user, pk)
        lesson = generics.get_object_or_404(
            DidacticLesson.objects.prefetch_related("sections", "sources"),
            learning_target_type=ContentType.objects.get_for_model(unit),
            learning_target_id=unit.id,
            audience=DidacticLesson.Audience.SENSEI,
        )
        snapshot = build_export_snapshot(lesson)
        exporters = {
            "docx": (render_lesson_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "html": (render_lesson_html, "text/html; charset=utf-8"),
        }
        if export_format not in exporters:
            return Response({"detail": "Formato de exportação não suportado."}, status=status.HTTP_404_NOT_FOUND)
        renderer, content_type = exporters[export_format]
        response = HttpResponse(renderer(snapshot), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{export_filename(snapshot, export_format)}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class SenseiDidacticPublicationPreviewView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        unit = _visible_unit(request.user, pk)
        serializer = DidacticPublicationPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            publication = create_preview(unit, serializer.validated_data["scope"], request.user)
        except DidacticPublicationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({
            "preview_token": str(publication.preview_token), "scope": publication.scope,
            "status": publication.status, "formation_id": publication.formation_id,
            "summary": publication.summary, "eligibility_items": publication.eligibility_items,
            "items": publication.preview_payload,
        }, status=status.HTTP_201_CREATED)


class SenseiDidacticPublicationPublishView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        unit = _visible_unit(request.user, pk)
        serializer = DidacticPublicationPublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            publication, published = publish_preview(serializer.validated_data["preview_token"], request.user, unit.module.formation_id)
        except DidacticPublicationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"status": publication.status, "scope": publication.scope, "published_at": publication.published_at, "items": published})


class SenseiAuthorshipChallengeView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get_lesson(self, request, pk):
        unit = _visible_unit(request.user, pk)
        lesson = generics.get_object_or_404(
            DidacticLesson.objects.prefetch_related("sections"),
            learning_target_type=ContentType.objects.get_for_model(unit),
            learning_target_id=unit.id,
            audience=DidacticLesson.Audience.SENSEI,
        )
        return lesson

    def get(self, request, pk):
        lesson = self.get_lesson(request, pk)
        section = get_authorship_section(lesson)
        if section is None:
            return Response({"section": None, "activity": None})
        activity = get_authorship_activity(lesson, section, request.user)
        return Response({"section": DidacticLessonSectionSerializer(section).data, "activity": SenseiLearningActivitySerializer(activity).data if activity else None})

    def post(self, request, pk):
        lesson = self.get_lesson(request, pk)
        section = get_authorship_section(lesson)
        if section is None:
            return Response({"detail": "Esta aula não possui Desafio de Autoria."}, status=status.HTTP_409_CONFLICT)
        try:
            activity, created = start_authorship_challenge(lesson, section, request.user)
        except DidacticContentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"section": DidacticLessonSectionSerializer(section).data, "activity": SenseiLearningActivitySerializer(activity).data}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SenseiUnitSourceListCreateView(generics.ListCreateAPIView):
    serializer_class = SenseiUnitSourceSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_unit(self):
        return _visible_unit(self.request.user, self.kwargs["unit_pk"])

    def get_queryset(self):
        return self.get_unit().curated_sources.select_related("source")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        unit = self.get_unit()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data.get("source")

        existing = None
        if source is not None:
            existing = (
                SenseiUnitSource.objects.select_for_update()
                .filter(unit=unit, source=source)
                .first()
            )

        if existing is not None:
            if existing.editorial_status != SenseiUnitSource.EditorialStatus.REJECTED:
                return Response(
                    {
                        "detail": (
                            "Esta fonte já possui uma proposta para esta unidade "
                            f"com status {existing.editorial_status}."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            previous_rejection = existing.rejection_reason.strip()
            for field, value in serializer.validated_data.items():
                if field != "source":
                    setattr(existing, field, value)

            if previous_rejection:
                history = f"Rejeição anterior: {previous_rejection}"
                existing.notes = "\n".join(
                    part for part in (existing.notes.strip(), history) if part
                )

            existing.curated_by = request.user
            existing.editorial_status = SenseiUnitSource.EditorialStatus.PROPOSED
            existing.rejection_reason = ""
            existing.reviewed_by = None
            existing.reviewed_at = None
            existing.save()

            return Response(
                SenseiUnitSourceSerializer(existing).data,
                status=status.HTTP_200_OK,
            )

        proposal = serializer.save(
            unit=unit,
            curated_by=request.user,
            editorial_status=SenseiUnitSource.EditorialStatus.PROPOSED,
        )
        return Response(
            SenseiUnitSourceSerializer(proposal).data,
            status=status.HTTP_201_CREATED,
        )


class SenseiUnitSourceReviewView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    @transaction.atomic
    def patch(self, request, pk):
        proposal = generics.get_object_or_404(
            SenseiUnitSource.objects.select_related("unit__module__formation").filter(
                Q(unit__module__formation__created_by=request.user) | Q(unit__module__formation__created_by__isnull=True)
            ), pk=pk,
        )
        serializer = SenseiUnitSourceReviewSerializer(data=request.data, context={"proposal": proposal})
        serializer.is_valid(raise_exception=True)
        proposal.editorial_status = serializer.validated_data["editorial_status"]
        proposal.rejection_reason = serializer.validated_data.get("rejection_reason", "") if proposal.editorial_status == SenseiUnitSource.EditorialStatus.REJECTED else ""
        proposal.reviewed_by = request.user
        proposal.reviewed_at = timezone.now()
        proposal.save(update_fields=["editorial_status", "rejection_reason", "reviewed_by", "reviewed_at", "updated_at"])
        if proposal.editorial_status == SenseiUnitSource.EditorialStatus.APPROVED:
            SenseiUnitSourceGap.objects.filter(unit=proposal.unit, status=SenseiUnitSourceGap.Status.OPEN).update(status=SenseiUnitSourceGap.Status.RESOLVED, resolved_by=request.user, resolved_at=timezone.now())
        return Response(SenseiUnitSourceSerializer(proposal).data)


class SenseiUnitSourceGapView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        unit = _visible_unit(request.user, pk)
        gap = SenseiUnitSourceGap.objects.filter(unit=unit).first()
        return Response(SenseiUnitSourceGapSerializer(gap).data if gap else {"status": "RESOLVED", "reason": ""})

    def patch(self, request, pk):
        unit = _visible_unit(request.user, pk)
        gap, _ = SenseiUnitSourceGap.objects.get_or_create(unit=unit, defaults={"reason": "Fonte adequada ainda não identificada.", "created_by": request.user})
        serializer = SenseiUnitSourceGapSerializer(gap, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        status_value = serializer.validated_data.get("status", gap.status)
        serializer.save(resolved_by=request.user if status_value == SenseiUnitSourceGap.Status.RESOLVED else None, resolved_at=timezone.now() if status_value == SenseiUnitSourceGap.Status.RESOLVED else None)
        return Response(serializer.data)


class SenseiStudyNoteListCreateView(generics.ListCreateAPIView):
    serializer_class = SenseiStudyNoteSerializer
    permission_classes = [IsLocalStudioAdmin]
    pagination_class = None

    def get_unit(self):
        return _visible_unit(self.request.user, self.kwargs["unit_pk"])

    def get_queryset(self):
        return self.get_unit().study_notes.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(unit=self.get_unit(), author=self.request.user)


class SenseiUnitStudyProgressView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def patch(self, request, pk):
        unit = _visible_unit(request.user, pk)
        progress, _ = SenseiUnitStudyProgress.objects.get_or_create(unit=unit, user=request.user)
        serializer = SenseiUnitStudyProgressSerializer(progress, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data.get("status", progress.status)
        now = timezone.now()
        progress = serializer.save(
            started_at=progress.started_at or (now if new_status != SenseiUnitStudyProgress.Status.NOT_STARTED else None),
            studied_at=now if new_status == SenseiUnitStudyProgress.Status.STUDIED else None,
        )
        # Deliberadamente não toca SenseiCompetencyProgress nem SenseiProgress.
        return Response(SenseiUnitStudyProgressSerializer(progress).data)


def _first_pedagogical_unit(formation):
    return (
        SenseiStudyUnit.objects.filter(module__formation=formation, status=SenseiStudyUnit.Status.ACTIVE)
        .select_related("module")
        .order_by("module__order", "module__id", "order", "id")
        .first()
    )


class SenseiStudyJourneyView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get_formation(self, request, formation_pk):
        return generics.get_object_or_404(_visible_formations(request.user), pk=formation_pk)

    def get(self, request, formation_pk):
        formation = self.get_formation(request, formation_pk)
        journey = SenseiStudyJourney.objects.select_related("current_unit__module").filter(
            formation=formation, user=request.user
        ).first()
        if journey:
            return Response(SenseiStudyJourneySerializer(journey).data)
        first_unit = _first_pedagogical_unit(formation)
        return Response({
            "id": None,
            "formation": formation.id,
            "user": request.user.id,
            "status": SenseiStudyJourney.Status.NOT_STARTED,
            "started_at": None,
            "current_unit": SenseiStudyUnitSerializer(first_unit).data if first_unit else None,
            "last_position": {},
            "created_at": None,
            "updated_at": None,
        })

    @transaction.atomic
    def post(self, request, formation_pk):
        formation = self.get_formation(request, formation_pk)
        first_unit = _first_pedagogical_unit(formation)
        if first_unit is None:
            return Response({"detail": "A formação não possui unidade ativa para iniciar."}, status=status.HTTP_409_CONFLICT)
        journey, created = SenseiStudyJourney.objects.get_or_create(
            formation=formation,
            user=request.user,
            defaults={
                "status": SenseiStudyJourney.Status.IN_PROGRESS,
                "started_at": timezone.now(),
                "current_unit": first_unit,
            },
        )
        # Idempotência: repetir INICIAR nunca reinicia data, unidade ou posição.
        if not created and journey.status == SenseiStudyJourney.Status.NOT_STARTED:
            journey.status = SenseiStudyJourney.Status.IN_PROGRESS
            journey.started_at = journey.started_at or timezone.now()
            journey.current_unit = journey.current_unit or first_unit
            journey.save(update_fields=["status", "started_at", "current_unit", "updated_at"])
        return Response(SenseiStudyJourneySerializer(journey).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def patch(self, request, formation_pk):
        formation = self.get_formation(request, formation_pk)
        journey = generics.get_object_or_404(SenseiStudyJourney, formation=formation, user=request.user)
        serializer = SenseiStudyJourneySerializer(journey, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SenseiUnitStartStudyView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    @transaction.atomic
    def post(self, request, pk):
        unit = _visible_unit(request.user, pk)
        formation = unit.module.formation
        now = timezone.now()
        journey, _ = SenseiStudyJourney.objects.get_or_create(
            formation=formation,
            user=request.user,
            defaults={
                "status": SenseiStudyJourney.Status.IN_PROGRESS,
                "started_at": now,
                "current_unit": unit,
            },
        )
        update_fields = []
        if journey.status == SenseiStudyJourney.Status.NOT_STARTED:
            journey.status = SenseiStudyJourney.Status.IN_PROGRESS
            update_fields.append("status")
        if journey.started_at is None:
            journey.started_at = now
            update_fields.append("started_at")
        if journey.current_unit_id != unit.id:
            journey.current_unit = unit
            journey.last_position = {}
            update_fields.extend(("current_unit", "last_position"))
        if update_fields:
            journey.save(update_fields=[*update_fields, "updated_at"])

        unit_progress, created = SenseiUnitStudyProgress.objects.get_or_create(
            unit=unit,
            user=request.user,
            defaults={"status": SenseiUnitStudyProgress.Status.STUDYING, "started_at": now},
        )
        if not created and unit_progress.status == SenseiUnitStudyProgress.Status.NOT_STARTED:
            unit_progress.status = SenseiUnitStudyProgress.Status.STUDYING
            unit_progress.started_at = unit_progress.started_at or now
            unit_progress.save(update_fields=["status", "started_at", "updated_at"])

        return Response({
            "journey": SenseiStudyJourneySerializer(journey).data,
            "study_progress": SenseiUnitStudyProgressSerializer(unit_progress).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SenseiLearningActivityListCreateView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, unit_pk):
        unit = _visible_unit(request.user, unit_pk)
        activities = unit.learning_activities.filter(user=request.user).select_related("competency").prefetch_related("attempts")[:50]
        return Response(SenseiLearningActivitySerializer(activities, many=True).data)

    def post(self, request, unit_pk):
        unit = _visible_unit(request.user, unit_pk)
        competency = None
        if request.data.get("competency_id") is not None:
            competency = generics.get_object_or_404(unit.study_plan.related_competencies, pk=request.data["competency_id"])
        try:
            activity = generate_activity(unit, request.user, competency)
        except SenseiLearningError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except (AIProviderError, RuntimeError):
            logger.warning("Falha segura ao gerar atividade do Sensei", exc_info=True)
            return Response({"detail": "O Sensei de Aprendizagem está temporariamente indisponível."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(SenseiLearningActivitySerializer(activity).data, status=status.HTTP_201_CREATED)


class SenseiLearningActivityAnswerView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        activity = generics.get_object_or_404(
            SenseiLearningActivity.objects.select_related("unit__module__formation", "competency"), pk=pk, user=request.user
        )
        serializer = SenseiLearningAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            activity = review_response(activity, serializer.validated_data["response"])
        except (AIProviderError, RuntimeError):
            logger.warning("Falha segura ao revisar atividade do Sensei", exc_info=True)
            return Response({"detail": "O Sensei de Aprendizagem está temporariamente indisponível."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(SenseiLearningActivitySerializer(activity).data)
