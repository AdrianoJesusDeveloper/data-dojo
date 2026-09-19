from django.core.management.base import BaseCommand

from library.models import Book
from library.reader_api import ensure_sections
from library.services.book_storage import identity_lock, backfill_hashes, book_path
from library.services.media_assets import generate_cover


class Command(BaseCommand):
    help = "Completa hashes, capas e seções sem apagar livros ou reprocessar embeddings."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--book-id", type=int)

    def handle(self, *args, **options):
        queryset = Book.objects.order_by("pk")
        if options["book_id"]:
            queryset = queryset.filter(pk=options["book_id"])
        if options["dry_run"]:
            self.stdout.write(f"DRY RUN: {queryset.count()} livros; {queryset.filter(sha256='').count()} sem hash; {queryset.filter(cover_asset__isnull=True).count()} sem capa. Nenhuma alteração.")
            return
        with identity_lock():
            backfill_hashes()
        for book in queryset.iterator():
            try:
                book_path(book)
                generate_cover(book)
                if book.status == "ready":
                    ensure_sections(book)
                self.stdout.write(f"Livro {book.pk}: metadata verificada.")
            except Exception as exc:
                self.stderr.write(f"Livro {book.pk}: {type(exc).__name__}; arquivo e dados preservados.")
