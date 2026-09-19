"""Library and reader endpoints, retaining the existing local-admin boundary."""
import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Prefetch
from django.http import FileResponse, StreamingHttpResponse
from rest_framework import generics, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book, BookSection, BookTocEntry, MediaAsset, ReadingProgress, ReadingMark
from .permissions import IsLocalStudioAdmin
from .services.book_storage import book_path
from .services.catalog import resolve_library_file
from .services.media_assets import create_asset
from .services.reader_content import flow_sections

MESSAGES = {"MISSING": "Arquivo não encontrado no caminho configurado.", "UNSUPPORTED": "Este formato ainda não é suportado.", "FAILED": "Não foi possível concluir o processamento. Consulte os logs do servidor.", "OCR_FAILED": "O OCR falhou ao processar uma ou mais páginas.", "PROCESSING": "O livro está sendo processado.", "WAITING": "Aguardando processamento.", "ARCHIVED": "Livro arquivado. Restaure para abrir.", "DISCARDED": "Livro descartado. Restaure para abrir."}


def availability(book):
    if book.lifecycle != "active":
        return book.lifecycle.upper()
    if book.status == "processing":
        return "PROCESSING"
    if Path(book.file.name).suffix.lower() not in {".pdf", ".epub", ".docx", ".txt"}:
        return "UNSUPPORTED"
    try:
        book_path(book)
    except (OSError, ValueError):
        return "MISSING"
    if book.status == "error":
        return "FAILED"
    return "AVAILABLE" if book.status == "ready" else "WAITING"


class LibraryPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class ProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = ("location", "position", "offset", "progress_percentage", "updated_at")
        read_only_fields = ("updated_at",)


class LibraryBookSerializer(serializers.ModelSerializer):
    format = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    reading = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ("id", "title", "author", "category", "format", "status", "availability", "message", "lifecycle", "is_favorite", "cover_asset", "cover_url", "progress_percent", "progress_stage", "error_code", "error_stage", "reading", "duplicate_of")
        read_only_fields = fields

    def get_format(self, obj):
        return Path(obj.file.name).suffix.lstrip(".").lower()

    def get_availability(self, obj):
        return availability(obj)

    def get_message(self, obj):
        state = availability(obj)
        return MESSAGES.get(obj.error_code if state == "FAILED" else state, "")

    def get_cover_url(self, obj):
        return f"/api/library/media/{obj.cover_asset_id}/file/" if obj.cover_asset_id else None

    def get_reading(self, obj):
        records = getattr(obj, "user_reading", None)
        progress = records[0] if records else obj.reading_progress.filter(user=self.context["request"].user).first() if records is None else None
        return ProgressSerializer(progress).data if progress else None


class LibraryBooksView(generics.ListAPIView):
    permission_classes = [IsLocalStudioAdmin]
    serializer_class = LibraryBookSerializer
    pagination_class = LibraryPagination

    def get_queryset(self):
        params = self.request.query_params
        queryset = Book.objects.select_related("cover_asset").prefetch_related(Prefetch("reading_progress", queryset=ReadingProgress.objects.filter(user=self.request.user), to_attr="user_reading"))
        lifecycle = params.get("lifecycle", "active")
        if lifecycle != "all":
            queryset = queryset.filter(lifecycle=lifecycle)
        search = params.get("search", "").strip()[:200]
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(author__icontains=search))
        for field in ("status", "category"):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get("format"):
            queryset = queryset.filter(file__iendswith="." + params["format"])
        if params.get("favorite") == "true":
            queryset = queryset.filter(is_favorite=True)
        return queryset


class BookUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("title", "author", "category", "is_favorite", "lifecycle", "cover_asset")


class LibraryBookDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsLocalStudioAdmin]
    queryset = Book.objects.all()

    def get_serializer_class(self):
        return LibraryBookSerializer if self.request.method == "GET" else BookUpdateSerializer

    def delete(self, request, pk):
        if request.data.get("confirmation") != f"EXCLUIR {pk}":
            raise ValidationError({"detail": f"Confirme explicitamente com EXCLUIR {pk}."})
        with transaction.atomic():
            book = generics.get_object_or_404(Book.objects.select_for_update(), pk=pk)
            if book.status == "processing":
                return Response({"detail": "Aguarde o processamento antes de excluir."}, status=409)
            related = book.scripts.exists() or book.studio_projects.exists() or book.duplicates.exists() or book.reading_marks.exists() or book.reading_progress.exists()
            cited = book.chunks.filter(Q(sourcecitation__isnull=False) | Q(studio_research_evidence__isnull=False)).exists()
            curated = book.source_id and book.source.sensei_unit_links.exists()
            if related or cited or curated:
                return Response({"detail": "O livro possui histórico ou dependências. Prefira arquivá-lo."}, status=409)
            # Never delete the source document or shared media; only the confirmed record.
            book.delete()
        return Response(status=204)


class BookCoverView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def post(self, request, pk):
        book = generics.get_object_or_404(Book, pk=pk)
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError("Selecione uma imagem.")
        asset = create_asset(upload, request.user, "BOOK_COVER")
        book.cover_asset = asset
        book.save(update_fields=["cover_asset"])
        return Response(LibraryBookSerializer(book, context={"request": request}).data)


class MediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = ("id", "title", "description", "original_filename", "mime_type", "file_size", "width", "height", "sha256", "category", "source_type", "source_url", "author", "license", "is_favorite", "created_at", "url")
        read_only_fields = ("id", "original_filename", "mime_type", "file_size", "width", "height", "sha256", "source_type", "created_at", "url")

    def get_url(self, obj):
        return f"/api/library/media/{obj.pk}/file/"


class MediaListView(generics.ListAPIView):
    permission_classes = [IsLocalStudioAdmin]
    serializer_class = MediaSerializer
    pagination_class = LibraryPagination

    def get_queryset(self):
        queryset = MediaAsset.objects.order_by("-created_at")
        if self.request.query_params.get("category"):
            queryset = queryset.filter(category=self.request.query_params["category"])
        if self.request.query_params.get("favorite") == "true":
            queryset = queryset.filter(is_favorite=True)
        if self.request.query_params.get("search"):
            queryset = queryset.filter(title__icontains=self.request.query_params["search"][:200])
        return queryset

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError("Selecione uma imagem.")
        asset = create_asset(upload, request.user, request.data.get("category", "OTHER"), title=request.data.get("title", ""))
        return Response(MediaSerializer(asset).data, status=201)


class MediaDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsLocalStudioAdmin]
    serializer_class = MediaSerializer
    queryset = MediaAsset.objects.all()


class MediaFileView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        asset = generics.get_object_or_404(MediaAsset, pk=pk)
        try:
            path = resolve_library_file(Path(settings.MEDIA_ROOT), Path(asset.file.name))
        except (ValueError, OSError):
            return Response({"detail": "Imagem indisponível."}, status=404)
        response = FileResponse(path.open("rb"), content_type=asset.mime_type)
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response


def readable_book(pk):
    book = generics.get_object_or_404(Book, pk=pk)
    state = availability(book)
    if state != "AVAILABLE":
        raise ValidationError({"detail": MESSAGES.get(state, "Livro indisponível."), "availability": state})
    return book


def ensure_sections(book):
    if book.sections.exists():
        return
    # Compatibility for processed books predating sections. No OCR/embedding rerun.
    if Path(book.file.name).suffix.lower() == ".pdf":
        sections = {}
        for chunk in book.chunks.order_by("chunk_index"):
            position = chunk.page_number or 1
            sections.setdefault(position, []).append(chunk.content)
        values = [dict(position=n, location=f"page:{n}", title=f"Página {n}", text="\n".join(text)) for n, text in sections.items()]
    else:
        values = flow_sections(book_path(book))
    BookSection.objects.bulk_create([BookSection(book=book, **value) for value in values], ignore_conflicts=True)


def reader_total(book):
    count = book.sections.count()
    if Path(book.file.name).suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(book_path(book)) as document:
            count = len(document)
    return count


def reader_toc(book):
    manual = list(book.manual_toc_entries.order_by("order", "id"))
    if not manual:
        return "automatic", list(book.sections.values("position", "location", "title"))

    pdf = Path(book.file.name).suffix.lower() == ".pdf"
    section_locations = {}
    if not pdf:
        positions = [entry.position for entry in manual]
        section_locations = dict(
            book.sections.filter(position__in=positions).values_list("position", "location")
        )

    entries = [
        {
            "id": entry.pk,
            "position": entry.position,
            "location": f"page:{entry.position}" if pdf else section_locations.get(entry.position, f"section:{entry.position}"),
            "title": entry.title,
            "order": entry.order,
        }
        for entry in manual
    ]
    return "manual", entries


class TocEntryInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)
    position = serializers.IntegerField(min_value=1)


class TocReplaceSerializer(serializers.Serializer):
    entries = TocEntryInputSerializer(many=True)

    def validate_entries(self, entries):
        if not entries:
            raise serializers.ValidationError("Adicione pelo menos um item ao índice.")
        if len(entries) > 500:
            raise serializers.ValidationError("O índice pode ter no máximo 500 itens.")
        return entries


class ReaderTocView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        book = readable_book(pk)
        try:
            ensure_sections(book)
            mode, entries = reader_toc(book)
        except (ValueError, OSError, KeyError, IndexError) as exc:
            raise ValidationError("Não foi possível carregar o índice deste documento.") from exc
        return Response({"mode": mode, "entries": entries})

    def put(self, request, pk):
        book = readable_book(pk)
        serializer = TocReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ensure_sections(book)
            total = reader_total(book)
        except (ValueError, OSError, KeyError, IndexError) as exc:
            raise ValidationError("Não foi possível validar as posições do índice.") from exc

        entries = serializer.validated_data["entries"]
        invalid = [entry["position"] for entry in entries if entry["position"] > total]
        if invalid:
            raise ValidationError({"entries": f"Posição fora do documento: {invalid[0]}. Máximo: {total}."})

        with transaction.atomic():
            Book.objects.select_for_update().get(pk=book.pk)
            BookTocEntry.objects.filter(book=book).delete()
            BookTocEntry.objects.bulk_create(
                [
                    BookTocEntry(
                        book=book,
                        title=entry["title"],
                        position=entry["position"],
                        order=index,
                    )
                    for index, entry in enumerate(entries, start=1)
                ]
            )

        mode, saved = reader_toc(book)
        return Response({"mode": mode, "entries": saved})

    def delete(self, request, pk):
        book = readable_book(pk)
        with transaction.atomic():
            Book.objects.select_for_update().get(pk=book.pk)
            BookTocEntry.objects.filter(book=book).delete()
        ensure_sections(book)
        mode, entries = reader_toc(book)
        return Response({"mode": mode, "entries": entries})


class ReaderMetadataView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        book = readable_book(pk)
        try:
            ensure_sections(book)
            count = reader_total(book)
            toc_mode, toc = reader_toc(book)
        except (ValueError, OSError, KeyError, IndexError) as exc:
            raise ValidationError("Não foi possível abrir este documento para leitura.") from exc
        automatic_toc = list(book.sections.values("position", "location", "title"))
        return Response({"book": LibraryBookSerializer(book, context={"request": request}).data, "total": count, "toc": toc, "automatic_toc": automatic_toc, "toc_mode": toc_mode, "file_url": f"/api/library/books/{pk}/file/"})


class ReaderFileView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        book = readable_book(pk)
        path = book_path(book)
        if path.suffix.lower() != ".pdf":
            raise ValidationError("Use a leitura segura por seção para este formato.")
        size = path.stat().st_size
        content_type = "application/pdf"
        range_header = request.headers.get("Range", "")
        if range_header:
            import re
            match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
            if not match:
                return Response(status=416, headers={"Content-Range": f"bytes */{size}"})
            start = int(match[1]); end = min(int(match[2]) if match[2] else size - 1, size - 1)
            if start > end or start >= size:
                return Response(status=416, headers={"Content-Range": f"bytes */{size}"})
            def chunks():
                with path.open("rb") as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        block = stream.read(min(65536, remaining))
                        if not block:
                            break
                        remaining -= len(block)
                        yield block
            response = StreamingHttpResponse(chunks(), status=206, content_type=content_type)
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
            response["Content-Length"] = end - start + 1
        else:
            response = FileResponse(path.open("rb"), content_type=content_type)
        response["Accept-Ranges"] = "bytes"
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ReaderSectionView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk, position):
        book = readable_book(pk)
        section = generics.get_object_or_404(book.sections, position=position)
        return Response({"position": section.position, "location": section.location, "title": section.title, "text": section.text, "html": section.html})


def validate_location(book, data):
    position = data.get("position", 1)
    if position < 1:
        raise ValidationError("Posição inválida.")
    if Path(book.file.name).suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(book_path(book)) as document:
            if position > len(document):
                raise ValidationError("Página inválida.")
            data["location"] = f"page:{position}"
    else:
        section = book.sections.filter(position=position).first()
        if section is None:
            raise ValidationError("Seção inválida.")
        data["location"] = section.location


class ReaderProgressView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        book = readable_book(pk)
        progress = ReadingProgress.objects.filter(book=book, user=request.user).first()
        return Response(ProgressSerializer(progress).data if progress else {})

    def put(self, request, pk):
        book = readable_book(pk)
        serializer = ProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        validate_location(book, data)
        progress, _ = ReadingProgress.objects.update_or_create(book=book, user=request.user, defaults=data)
        return Response(ProgressSerializer(progress).data)


class MarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingMark
        fields = ("id", "kind", "location", "position", "offset", "selected_text", "start_offset", "end_offset", "note", "created_at", "updated_at")
        read_only_fields = ("id", "location", "created_at", "updated_at")
        extra_kwargs = {"note": {"max_length": 20000}, "selected_text": {"max_length": 10000}}

    def validate(self, data):
        kind = data.get("kind", getattr(self.instance, "kind", None))
        if kind == "annotation" and not data.get("note", getattr(self.instance, "note", "")).strip():
            raise ValidationError("Escreva uma anotação.")
        if kind == "highlight":
            selected = data.get("selected_text", getattr(self.instance, "selected_text", ""))
            start = data.get("start_offset", getattr(self.instance, "start_offset", None))
            end = data.get("end_offset", getattr(self.instance, "end_offset", None))
            if not selected or start is None or end is None or end <= start:
                raise ValidationError("Selecione um trecho de texto válido.")
        return data


class ReaderMarksView(generics.ListCreateAPIView):
    permission_classes = [IsLocalStudioAdmin]
    serializer_class = MarkSerializer
    pagination_class = LibraryPagination

    def get_queryset(self):
        return ReadingMark.objects.filter(book=readable_book(self.kwargs["pk"]), user=self.request.user)

    def perform_create(self, serializer):
        book = readable_book(self.kwargs["pk"])
        validate_location(book, serializer.validated_data)
        serializer.save(book=book, user=self.request.user)


class ReaderMarkDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsLocalStudioAdmin]
    serializer_class = MarkSerializer
    lookup_url_kwarg = "mark_pk"

    def get_queryset(self):
        return ReadingMark.objects.filter(book=readable_book(self.kwargs["pk"]), user=self.request.user)

    def perform_update(self, serializer):
        data = serializer.validated_data
        data.setdefault("position", serializer.instance.position)
        validate_location(serializer.instance.book, data)
        serializer.save()


class ReaderSearchView(APIView):
    permission_classes = [IsLocalStudioAdmin]

    def get(self, request, pk):
        book = readable_book(pk)
        term = request.query_params.get("q", "").strip()[:200]
        if len(term) < 2:
            return Response({"count": 0, "results": []})
        sections = book.sections.filter(text__icontains=term)
        results = []
        for section in sections[:100]:
            start = section.text.lower().find(term.lower())
            results.append({"position": section.position, "location": section.location, "title": section.title, "snippet": section.text[max(0, start - 80):start + len(term) + 160], "offset": max(start, 0) / max(len(section.text), 1)})
        return Response({"count": sections.count(), "results": results})
