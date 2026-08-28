from pathlib import Path
import logging
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Book, ContentPackage, EditorialComment, EditorialCouncilRun, EditorialPlanVersion, GeneratedScript,
    LibrarySource, ModernizationPlan, SourceCitation, StudioApproval, StudioProject, Trilha,
)
from .permissions import IsLocalStudioAdmin
from .serializers import (
    BookSerializer, BookStatusSerializer, GeneratedScriptSerializer, LibrarySourceSerializer,
    ApprovalInputSerializer, ContentGenerationInputSerializer, ContentPackageSerializer,
    EditorialCommentSerializer, EditorialCouncilRunSerializer, EditorialPlanEditSerializer, EditorialPlanVersionSerializer,
    GenerateScriptSerializer, StudioProjectSerializer, TrilhaSerializer,
)
from .services.generation import gerar_roteiro
from .services.retrieval import buscar_chunks_relevantes
from .services.catalog import scan_library
from .editorial_contracts import validate_editorial_plan
from .services.studio_agents import generate_content_item, generate_content_package, generate_modernization_plan
from .services.editorial_council import CouncilExecutionError, start_editorial_council
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
        return Response({
            "enabled": settings.DDJ_CONTENT_STUDIO_ENABLED,
            "local_only": settings.DDJ_CONTENT_STUDIO_LOCAL_ONLY,
            "sources": sources.count(),
            "supported": sources.filter(status="supported").count(),
            "unsupported": sources.filter(status="unsupported").count(),
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
        duplicate = LibrarySource.objects.filter(sha256=OuterRef("sha256")).exclude(pk=OuterRef("pk"))
        queryset = LibrarySource.objects.select_related("book").annotate(
            _duplicate=Case(When(sha256="", then=Value(False)), default=Exists(duplicate), output_field=BooleanField())
        )
        status_filter = self.request.query_params.get("status")
        rag_status = self.request.query_params.get("rag_status")
        extension = self.request.query_params.get("extension")
        search = self.request.query_params.get("search", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
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
                LibrarySource.objects.select_for_update().select_related("book"), pk=pk
            )
            if source.status != "supported" or source.extension.lower() != "pdf":
                return Response(
                    {"detail": "Esta fonte não está disponível para processamento."},
                    status=status.HTTP_409_CONFLICT,
                )
            if source.sha256 and LibrarySource.objects.filter(sha256=source.sha256).exclude(pk=source.pk).exists():
                return Response(
                    {"detail": "Fontes duplicadas não podem ser processadas."},
                    status=status.HTTP_409_CONFLICT,
                )

            book = getattr(source, "book", None)
            if book is None:
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
                book = Book(title=Path(source.filename).stem[:255], source=source)
                with candidate.open("rb") as stream:
                    book.file.save(Path(source.filename).name, File(stream), save=False)
                book.save()

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

            previous_status = book.status
            book.status = "processing"
            book.error_message = ""
            book.save(update_fields=["status", "error_message"])
            try:
                result = process_book.delay(book.id)
            except Exception:
                book.status = previous_status
                book.save(update_fields=["status"])
                return Response(
                    {"detail": "Não foi possível acessar a fila de processamento."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        return Response(
            {
                "source_id": source.id,
                "book_id": book.id,
                "task_id": result.id,
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
        return StudioProject.objects.filter(created_by=self.request.user, is_archived=archived).prefetch_related("books", "citations", "approvals", "editorial_comments")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class StudioProjectDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = StudioProjectSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        return StudioProject.objects.filter(created_by=self.request.user).prefetch_related("books", "citations", "approvals", "editorial_comments")


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
        if not books:
            return Response({"detail": "Vincule ao menos um livro processado ao projeto."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            project = StudioProject.objects.select_for_update().get(pk=project.pk)
            existing_plan = ModernizationPlan.objects.filter(project=project).first()
            expected_version = existing_plan.version if existing_plan else 0
            previous_plan = existing_plan.proposed_architecture if existing_plan else None
            project.status = "planning"
            project.save(update_fields=["status", "updated_at"])
        try:
            chunks = buscar_chunks_relevantes(f"{project.theme}\n{project.objective}", [book.id for book in books], top_k=10)
            if not chunks:
                raise ValueError("Nenhuma fonte relevante foi recuperada.")
            data, raw = generate_modernization_plan(project, chunks, previous_plan)
        except (RuntimeError, ValueError) as exc:
            with transaction.atomic():
                locked_project = StudioProject.objects.select_for_update().get(pk=project.pk)
                current = ModernizationPlan.objects.filter(project=locked_project).first()
                current_version = current.version if current else 0
                if locked_project.status == "planning" and current_version == expected_version:
                    locked_project.status = "draft"
                    locked_project.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "Não foi possível gerar o plano de modernização."},
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
        if project.project_type == "youtube":
            collection = plan_data.get("videos", [])
            if target_type != "video":
                return Response({"detail": "Trilhas YouTube geram um vÃ­deo por vez."}, status=status.HTTP_400_BAD_REQUEST)
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
            content, raw = generate_content_item(project, project.modernization_plan, target_type, target_index, target)
        except (RuntimeError, ValueError) as exc:
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
        return Response(ContentPackageSerializer(package).data)


class BookProcessView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        with transaction.atomic():
            book = generics.get_object_or_404(Book.objects.select_for_update(), pk=pk)
            if book.status == "processing":
                return Response({"detail": "Livro já está sendo processado."}, status=status.HTTP_409_CONFLICT)
            previous_status = book.status
            book.status = "processing"
            book.error_message = ""
            book.processed_at = None
            book.save(update_fields=["status", "error_message", "processed_at"])
            try:
                result = process_book.delay(book.id)
            except Exception:
                book.status = previous_status
                book.save(update_fields=["status"])
                return Response(
                    {"detail": "Não foi possível acessar a fila de processamento."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        return Response({"book_id": book.id, "task_id": result.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)


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
