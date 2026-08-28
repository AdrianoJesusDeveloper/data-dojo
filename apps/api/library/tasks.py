import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Book, BookChunk
from .services.embeddings import generate_embeddings
from .services.ingestion import chunk_text, extract_text_by_page


logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(), name="library.process_book")
def process_book(self, book_id: int):
    try:
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book_id)
            if book.status != "processing":
                return {"book_id": book.id, "status": book.status, "skipped": True}
            pages = extract_text_by_page(book.file.path)
            chunks = chunk_text(pages)
            embeddings = generate_embeddings([item["content"] for item in chunks])
            if len(chunks) != len(embeddings):
                raise ValueError("Quantidade de embeddings incompatÃ­vel com os chunks.")
            book.chunks.all().delete()
            BookChunk.objects.bulk_create([
                BookChunk(book=book, embedding=embedding, **item)
                for item, embedding in zip(chunks, embeddings)
            ])
            book.status = "ready"
            book.total_chunks = len(chunks)
            book.processed_at = timezone.now()
            book.error_message = ""
            book.save(update_fields=["status", "total_chunks", "processed_at", "error_message"])
        return {"book_id": book.id, "total_chunks": len(chunks)}
    except Exception as exc:
        logger.exception("Falha ao processar o livro %s", book_id)
        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book_id)
            if book.status == "processing":
                book.status = "error"
                book.error_message = "Falha no processamento do PDF. Consulte os logs do servidor."
                book.save(update_fields=["status", "error_message"])
        raise
