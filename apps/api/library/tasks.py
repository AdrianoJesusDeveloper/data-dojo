import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Book, BookChunk
from .services.embeddings import generate_embeddings
from .services.ingestion import chunk_text, extract_document


logger = logging.getLogger(__name__)


def _set_progress(book_id: int, percent: int, stage: str):
    Book.objects.filter(pk=book_id).update(
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
        pages = extract_document(book.file.path)

        _set_progress(book_id, 45, "Fragmentando conteúdo")
        chunks = chunk_text(pages)

        _set_progress(book_id, 60, "Gerando embeddings")
        embeddings = generate_embeddings([item["content"] for item in chunks])

        if len(chunks) != len(embeddings):
            raise ValueError("Quantidade de embeddings incompatível com os chunks.")

        _set_progress(book_id, 90, "Salvando índice")
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book_id)
            if book.status != "processing":
                return {"book_id": book.id, "status": book.status, "skipped": True}

            book.chunks.all().delete()
            BookChunk.objects.bulk_create([
                BookChunk(book=book, embedding=embedding, **item)
                for item, embedding in zip(chunks, embeddings)
            ])

            book.status = "ready"
            book.total_chunks = len(chunks)
            book.processed_at = timezone.now()
            book.error_message = ""
            book.progress_percent = 100
            book.progress_stage = "Concluído"
            book.save(update_fields=[
                "status",
                "total_chunks",
                "processed_at",
                "error_message",
                "progress_percent",
                "progress_stage",
            ])

        return {"book_id": book.id, "total_chunks": len(chunks)}

    except Exception:
        logger.exception("Falha ao processar o livro %s", book_id)
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book_id)
            if book.status == "processing":
                book.status = "error"
                book.error_message = "Falha no processamento do documento. Consulte os logs do servidor."
                book.progress_stage = "Falha no processamento"
                book.save(update_fields=["status", "error_message", "progress_stage"])
        raise
