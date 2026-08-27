from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Book, ContentPackage, GeneratedScript, LibrarySource, ModernizationPlan,
    SourceCitation, StudioApproval, StudioProject, Trilha,
)
from .permissions import IsLocalStudioAdmin
from .serializers import (
    BookSerializer, BookStatusSerializer, GeneratedScriptSerializer, LibrarySourceSerializer,
    ApprovalInputSerializer, ContentPackageSerializer, GenerateScriptSerializer,
    StudioProjectSerializer, TrilhaSerializer,
)
from .services.generation import gerar_roteiro
from .services.retrieval import buscar_chunks_relevantes
from .services.catalog import scan_library
from .services.studio_agents import generate_content_package, generate_modernization_plan
from .tasks import process_book


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
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class LibrarySourceListView(generics.ListAPIView):
    serializer_class = LibrarySourceSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        queryset = LibrarySource.objects.all()
        status_filter = self.request.query_params.get("status")
        extension = self.request.query_params.get("extension")
        search = self.request.query_params.get("search", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if extension:
            queryset = queryset.filter(extension=extension.lstrip(".").lower())
        if search:
            queryset = queryset.filter(relative_path__icontains=search)
        return queryset


class StudioProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = StudioProjectSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        return StudioProject.objects.filter(created_by=self.request.user).prefetch_related("books", "citations", "approvals")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class StudioProjectDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = StudioProjectSerializer
    permission_classes = [IsLocalStudioAdmin]

    def get_queryset(self):
        return StudioProject.objects.filter(created_by=self.request.user).prefetch_related("books", "citations", "approvals")


class StudioGeneratePlanView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        books = list(project.books.filter(status="ready"))
        if not books:
            return Response({"detail": "Vincule ao menos um livro processado ao projeto."}, status=status.HTTP_400_BAD_REQUEST)
        project.status = "planning"
        project.save(update_fields=["status", "updated_at"])
        try:
            chunks = buscar_chunks_relevantes(f"{project.theme}\n{project.objective}", [book.id for book in books], top_k=10)
            if not chunks:
                raise ValueError("Nenhuma fonte relevante foi recuperada.")
            data, raw = generate_modernization_plan(project, chunks)
        except (RuntimeError, ValueError) as exc:
            project.status = "draft"
            project.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "Não foi possível gerar o plano de modernização."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            previous = ModernizationPlan.objects.filter(project=project).first()
            version = (previous.version + 1) if previous else 1
            plan, _ = ModernizationPlan.objects.update_or_create(project=project, defaults={**data, "raw_response": raw, "status": "review", "version": version})
            project.citations.filter(purpose="modernization_plan").delete()
            SourceCitation.objects.bulk_create([
                SourceCitation(project=project, chunk=chunk, book_title=chunk.book.title, page_number=chunk.page_number, excerpt=chunk.content[:1500])
                for chunk in chunks
            ])
            project.status = "awaiting_approval"
            project.save(update_fields=["status", "updated_at"])
        return Response(StudioProjectSerializer(project).data)


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
            project.status = "approved" if decision == "approved" else "planning"
            project.save(update_fields=["status", "updated_at"])
        return Response(StudioProjectSerializer(project).data)


class StudioGenerateContentView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        project = generics.get_object_or_404(StudioProject, pk=pk, created_by=request.user)
        if not hasattr(project, "modernization_plan") or project.modernization_plan.status != "approved":
            return Response({"detail": "Aprove o plano de modernização antes de gerar conteúdo."}, status=status.HTTP_409_CONFLICT)
        try:
            data, raw = generate_content_package(project, project.modernization_plan)
        except (RuntimeError, ValueError) as exc:
            return Response(
                {"detail": "Não foi possível gerar o pacote de conteúdo."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        package, _ = ContentPackage.objects.update_or_create(project=project, defaults={**data, "raw_response": raw})
        project.status = "content"
        project.save(update_fields=["status", "updated_at"])
        return Response(ContentPackageSerializer(package).data)


class BookProcessView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        book = generics.get_object_or_404(Book, pk=pk)
        if book.status == "processing":
            return Response({"detail": "Livro já está sendo processado."}, status=status.HTTP_409_CONFLICT)
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
