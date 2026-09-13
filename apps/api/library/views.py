from pathlib import Path
import logging
from uuid import uuid4

from django.conf import settings
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
from .services.studio_agents import generate_content_item, generate_content_package, generate_modernization_plan
from .services.editorial_council import CouncilExecutionError, start_editorial_council
from .services.council_export import COUNCIL_EXPORT_MIMES, council_export_filename, render_council_export
from .services.sensei_learning import SenseiLearningError, available_providers, generate_activity, resolve_provider, review_response
from .services.didactic_content import DidacticContentError, generate_didactic_lesson, get_authorship_activity, get_authorship_section, start_authorship_challenge, update_human_lesson
from .services.didactic_export import build_export_snapshot, export_filename, render_lesson_docx, render_lesson_html
from .services.didactic_publication import DidacticPublicationError, create_preview, publish_preview
from .services.studio_export import artifact_filename, render_artifact_docx, render_artifact_html
from .services.studio_plan_export import MIMES as PLAN_EXPORT_MIMES, export_filename as plan_export_filename, render_plan_export
from .services.studio_formation import StudioFormationError, materialize_premium_formation
from .services.studio_research import StudioResearchError, build_research_context, generate_grounded_dossier, research_prompt_context
from ai.services import AIProviderError, canonical_provider_name, provider_is_available
from .tasks import process_book


logger = logging.getLogger(__name__)


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
        with transaction.atomic():
            source = generics.get_object_or_404(
                LibrarySource.objects.select_for_update().prefetch_related("book"), pk=pk
            )
            if source.status != "supported" or source.extension.lower() not in {"pdf", "epub"}:
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
                    book = Book(title=Path(source.filename).stem[:255], source=source)

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
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        books = list(project.books.filter(status="ready"))
        if project.research_policy == "ACERVO_ONLY" and not books:
            return Response({"detail": "Vincule ao menos um livro processado ao projeto."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            project = StudioProject.objects.select_for_update().get(pk=project.pk)
            existing_plan = ModernizationPlan.objects.filter(project=project).first()
            expected_version = existing_plan.version if existing_plan else 0
            previous_plan = existing_plan.proposed_architecture if existing_plan else None
            project.status = "planning"
            project.save(update_fields=["status", "updated_at"])
        try:
            chunks = buscar_chunks_relevantes(f"{project.theme}\n{project.objective}", [book.id for book in books], top_k=10) if books else []
            if project.research_policy == "ACERVO_ONLY" and not chunks:
                raise ValueError("Nenhuma fonte relevante foi recuperada.")
            grounded_context = ""
            if hasattr(project, "research_context"):
                try:
                    grounded_context = research_prompt_context(project)
                except StudioResearchError:
                    # Um contexto GAP/insuficiente não deve impedir um rascunho
                    # sem fontes quando a política permite geração não fundamentada.
                    # ACERVO_ONLY continua protegido pelas validações acima.
                    if project.research_policy == "ACERVO_ONLY":
                        raise
                    grounded_context = ""

            data, raw = generate_modernization_plan(
                project,
                chunks,
                previous_plan,
                grounded_context,
            )
        except (RuntimeError, ValueError, StudioResearchError, AIProviderError) as exc:
            logger.exception(
                "Falha ao gerar plano editorial do projeto %s [%s]: %s",
                project.pk,
                type(exc).__name__,
                str(exc),
            )
            with transaction.atomic():
                locked_project = StudioProject.objects.select_for_update().get(pk=project.pk)
                current = ModernizationPlan.objects.filter(project=locked_project).first()
                current_version = current.version if current else 0
                if locked_project.status == "planning" and current_version == expected_version:
                    locked_project.status = "draft"
                    locked_project.save(update_fields=["status", "updated_at"])
            return Response(
                {
                    "detail": (
                        "Não foi possível gerar o plano editorial. "
                        "Consulte o log do servidor para identificar a causa técnica."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            locked_project = StudioProject.objects.select_for_update().get(pk=project.pk)
            previous = ModernizationPlan.objects.select_for_update().filter(project=locked_project).first()
            current_version = previous.version if previous else 0
            if current_version != expected_version:
                return Response(
                    {"detail": "O plano mudou durante a geraÃ§Ã£o; gere novamente."},
                    status=status.HTTP_409_CONFLICT,
                )
            if previous:
                _record_plan_version(locked_project, previous, request.user, "revision")
            version = (previous.version + 1) if previous else 1
            plan, _ = ModernizationPlan.objects.update_or_create(project=locked_project, defaults={**data, "raw_response": raw, "status": "review", "version": version})
            _record_plan_version(locked_project, plan, request.user, "ai")
            locked_project.citations.filter(purpose="modernization_plan").delete()
            SourceCitation.objects.bulk_create([
                SourceCitation(project=locked_project, chunk=chunk, book_title=chunk.book.title, page_number=chunk.page_number, excerpt=chunk.content[:1500])
                for chunk in chunks
            ])
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
            )
        except AIProviderError as exc:
            logger.warning(
                "studio_content_generation_provider_failed project_id=%s target_type=%s "
                "target_index=%s provider=%s error_code=%s",
                project.pk,
                target_type,
                target_index,
                getattr(exc, "provider", "unknown"),
                getattr(exc, "code", "unknown"),
            )
            return Response(
                {"detail": "Não foi possível gerar o pacote de conteúdo."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
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


class StudioResearchView(APIView):
    permission_classes = [IsLocalStudioAdmin]

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

    def patch(self, request, pk):
        unit = self.get_unit(request, pk)
        lesson = generics.get_object_or_404(DidacticLesson, learning_target_type=ContentType.objects.get_for_model(unit), learning_target_id=unit.id, audience=DidacticLesson.Audience.SENSEI)
        serializer = DidacticLessonUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_status = serializer.validated_data.get("status")
        allowed = {"DRAFT": {"REVIEW", "ARCHIVED"}, "REVIEW": {"DRAFT", "APPROVED", "ARCHIVED"}, "APPROVED": {"REVIEW", "PUBLISHED", "ARCHIVED"}, "PUBLISHED": {"ARCHIVED"}, "ARCHIVED": {"DRAFT"}}
        if next_status and next_status != lesson.status and next_status not in allowed.get(lesson.status, set()):
            return Response({"detail": "Transição de status não permitida."}, status=status.HTTP_400_BAD_REQUEST)
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

    def perform_create(self, serializer):
        serializer.save(unit=self.get_unit(), curated_by=self.request.user, editorial_status=SenseiUnitSource.EditorialStatus.PROPOSED)


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
