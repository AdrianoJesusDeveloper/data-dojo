from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book, GeneratedScript, LibrarySource, Trilha
from .serializers import (
    BookSerializer, BookStatusSerializer, GeneratedScriptSerializer, LibrarySourceSerializer,
    GenerateScriptSerializer, TrilhaSerializer,
)
from .services.catalog import scan_library
from .services.generation import gerar_roteiro
from .services.retrieval import buscar_chunks_relevantes
from .tasks import process_book


class BookUploadView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Book.objects.select_related("trilha").all()


class LibraryScanView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        try:
            return Response(scan_library(), status=status.HTTP_200_OK)
        except (OSError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class LibrarySourceListView(generics.ListAPIView):
    serializer_class = LibrarySourceSerializer
    permission_classes = [permissions.IsAdminUser]

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


class BookProcessView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
    permission_classes = [permissions.IsAdminUser]


class TrilhaListView(generics.ListAPIView):
    queryset = Trilha.objects.all()
    serializer_class = TrilhaSerializer
    permission_classes = [permissions.IsAdminUser]


class ScriptGenerateView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = GeneratedScript.objects.select_related("trilha", "created_by").prefetch_related("books")
        return queryset if self.request.user.is_staff else queryset.filter(created_by=self.request.user)


class ScriptDetailView(generics.RetrieveAPIView):
    serializer_class = GeneratedScriptSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = GeneratedScript.objects.select_related("trilha", "created_by").prefetch_related("books")
        return queryset if self.request.user.is_staff else queryset.filter(created_by=self.request.user)
