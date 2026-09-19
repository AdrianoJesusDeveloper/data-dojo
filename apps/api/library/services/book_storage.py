"""Private file resolution and a shared, transactional content identity boundary."""
from contextlib import contextmanager
import hashlib
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from rest_framework.exceptions import APIException

from library.models import Book
from .catalog import resolve_library_file, _sha256


class DuplicateBook(APIException):
    status_code = 409
    default_code = "duplicate_book"

    def __init__(self, book):
        super().__init__({"detail": "Este livro já está cadastrado na Biblioteca.", "original_id": book.pk, "title": book.title})


def book_path(book):
    return resolve_library_file(Path(settings.MEDIA_ROOT), Path(book.file.name))


def stream_hash(stream):
    stream.seek(0)
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    stream.seek(0)
    return digest.hexdigest()


@contextmanager
def identity_lock():
    # PostgreSQL transaction lock serializes uploads, imports and historical backfill.
    # The partial unique constraint remains the final guard for all other writers.
    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [340032001])
        yield


def backfill_hashes():
    for book in Book.objects.filter(sha256="").order_by("pk").iterator():
        try:
            digest = _sha256(book_path(book))
        except (OSError, ValueError):
            continue
        original = Book.objects.filter(sha256=digest, duplicate_of__isnull=True).exclude(pk=book.pk).first()
        Book.objects.filter(pk=book.pk).update(sha256=digest, duplicate_of=original)


def check_duplicate(digest, exclude=None):
    backfill_hashes()
    original = Book.objects.filter(sha256=digest, duplicate_of__isnull=True).exclude(pk=exclude).first()
    if original:
        raise DuplicateBook(original)
