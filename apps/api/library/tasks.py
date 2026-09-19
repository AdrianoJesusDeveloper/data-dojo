import logging
from pathlib import Path

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Book, BookChunk, BookSection
from .services.embeddings import generate_embeddings
from .services.ingestion import chunk_text, extract_document, progress_callback, OCRFailure
from .services.reader_content import flow_sections
from .services.media_assets import generate_cover


logger = logging.getLogger(__name__)


def _set_progress(book_id: int, percent: int, stage: str):
    Book.objects.filter(pk=book_id, status="processing", progress_percent__lte=percent).update(
        progress_percent=percent,
        progress_stage=stage,
    )


@shared_task(bind=True, autoretry_for=(), name="library.process_book")
def process_book(self, book_id: int):
    try:
        book = Book.objects.get(pk=book_id)
        if book.status != "processing":
            return {"book_id": book.id, "status": book.status, "skipped": True}

        _set_progress(book_id, 5, "Preparando documento")

        _set_progress(book_id, 20, "Extraindo conteúdo")
        token = progress_callback.set(lambda current, total, stage: _set_progress(book_id, 20 + int(35 * current / max(total, 1)), stage))
        try:
            pages = extract_document(book.file.path)
        finally:
            progress_callback.reset(token)
        sections = flow_sections(book.file.path) if Path(book.file.name).suffix.lower() in {".epub", ".docx", ".txt"} else [dict(position=n, location=f"page:{n}", title=f"Página {n}", text=text) for n, text in pages]

        _set_progress(book_id, 60, "Preparando páginas")
        _set_progress(book_id, 70, "Fragmentando conteúdo")
        chunks = chunk_text(pages)

        _set_progress(book_id, 80, "Gerando embeddings")
        embeddings = []
        for start in range(0, len(chunks), 32):
            batch = chunks[start:start + 32]
            embeddings.extend(generate_embeddings([item["content"] for item in batch]))
            _set_progress(book_id, 80 + int(10 * min(start + 32, len(chunks)) / len(chunks)), "Gerando embeddings")

        if len(chunks) != len(embeddings):
            raise ValueError("Quantidade de embeddings incompatível com os chunks.")

        _set_progress(book_id, 90, "Salvando índice")
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book_id)
            if book.status != "processing":
                return {"book_id": book.id, "status": book.status, "skipped": True}

            book.chunks.all().delete()
            book.sections.all().delete()
            BookSection.objects.bulk_create([BookSection(book=book, **section) for section in sections])
            BookChunk.objects.bulk_create([
                BookChunk(book=book, embedding=embedding, **item)
                for item, embedding in zip(chunks, embeddings)
            ])

            book.status = "ready"
            book.total_chunks = len(chunks)
            book.processed_at = timezone.now()
            book.error_message = ""
            book.error_code = ""
            book.error_stage = ""
            book.technical_error = ""
            book.progress_percent = 100
            book.progress_stage = "Concluído"
            book.save(update_fields=[
                "status",
                "total_chunks",
                "processed_at",
                "error_message",
                "error_code", "error_stage", "technical_error",
                "progress_percent",
                "progress_stage",
            ])

        try:
            generate_cover(book)
        except Exception:
            logger.warning("Capa indisponível para livro %s; placeholder será utilizado.", book_id, exc_info=True)
        return {"book_id": book.id, "total_chunks": len(chunks)}

    except Exception as exc:
        logger.exception("Falha ao processar o livro %s", book_id)
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book_id)
            if book.status == "processing":
                book.status = "error"
                book.error_code = "OCR_FAILED" if isinstance(exc, OCRFailure) or "Tesseract" in str(exc) else "MISSING" if isinstance(exc, FileNotFoundError) else "UNSUPPORTED" if Path(book.file.name).suffix.lower() not in {".pdf", ".epub", ".docx", ".txt"} else "FAILED"
                book.error_stage = book.progress_stage
                book.technical_error = f"{type(exc).__name__}: {exc}"
                book.error_message = "Falha no processamento do documento. Consulte os logs do servidor."
                book.progress_stage = "Falha no processamento"
                book.save(update_fields=["status", "error_message", "progress_stage", "error_code", "error_stage", "technical_error"])
        raise
