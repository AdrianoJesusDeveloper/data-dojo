import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import Book, BookChunk, LibrarySource
from library.tasks import process_book


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class LibrarySourceProcessingTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            email="source-admin@example.com",
            username="source_admin",
            password="dojo-test-password",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "library"
        self.media = self.base / "media"
        self.root.mkdir()

    def create_source(self, name="livro.pdf", **overrides):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4\n%%EOF")
        values = {
            "relative_path": name,
            "filename": Path(name).name,
            "extension": "pdf",
            "size_bytes": path.stat().st_size,
            "sha256": f"hash-{name}",
            "status": "supported",
        }
        values.update(overrides)
        return LibrarySource.objects.create(**values)

    def request_process(self, source):
        with self.settings(LOCAL_LIBRARY_PATH=self.root, MEDIA_ROOT=self.media):
            return self.client.post(
                reverse("library-source-process", kwargs={"pk": source.pk}),
                {},
                format="json",
                REMOTE_ADDR="127.0.0.1",
            )

    @patch("library.views.process_book.delay")
    def test_supported_source_creates_book_and_enqueues_task(self, delay):
        delay.return_value.id = "task-123"
        source = self.create_source()

        response = self.request_process(source)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        book = Book.objects.get(source=source)
        self.assertEqual(book.status, "processing")
        self.assertEqual(response.data["book_id"], book.id)
        self.assertEqual(response.data["status"], "processing")
        self.assertIn(f"/api/library/books/{book.id}/status/", response.data["status_url"])
        self.assertNotIn(str(self.root), json.dumps(response.data))
        delay.assert_called_once_with(book.id)

    @patch("library.views.process_book.delay")
    def test_second_call_reuses_book_without_enqueuing_again(self, delay):
        delay.return_value.id = "task-123"
        source = self.create_source()
        first = self.request_process(source)
        second = self.request_process(source)

        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["status"], "processing")
        self.assertEqual(Book.objects.filter(source=source).count(), 1)
        delay.assert_called_once()

    def test_duplicate_missing_and_unsupported_sources_are_rejected(self):
        duplicate = self.create_source("duplicado.pdf", sha256="same-hash")
        self.create_source("copia.pdf", sha256="same-hash")
        missing = LibrarySource.objects.create(
            relative_path="ausente.pdf",
            filename="ausente.pdf",
            extension="pdf",
            sha256="missing-hash",
            status="missing",
        )
        unsupported = self.create_source(
            "notas.epub", extension="epub", status="unsupported", sha256="unsupported-hash"
        )

        self.assertEqual(self.request_process(duplicate).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.request_process(missing).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.request_process(unsupported).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Book.objects.count(), 0)

    def test_path_traversal_and_absolute_outside_path_are_rejected(self):
        outside = self.base / "outside.pdf"
        outside.write_bytes(b"%PDF-1.4\nprivate\n%%EOF")
        traversal = LibrarySource.objects.create(
            relative_path="../outside.pdf", filename="outside.pdf", extension="pdf",
            sha256="traversal", status="supported",
        )
        absolute = LibrarySource.objects.create(
            relative_path=str(outside.resolve()), filename="outside.pdf", extension="pdf",
            sha256="absolute", status="supported",
        )

        self.assertEqual(self.request_process(traversal).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.request_process(absolute).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Book.objects.count(), 0)

    def test_symlink_escaping_library_root_is_rejected(self):
        outside = self.base / "outside-link.pdf"
        outside.write_bytes(b"%PDF-1.4\nprivate\n%%EOF")
        link = self.root / "linked.pdf"
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"Symlinks indisponíveis neste ambiente: {exc}")
        source = LibrarySource.objects.create(
            relative_path="linked.pdf", filename="linked.pdf", extension="pdf",
            sha256="symlink", status="supported",
        )

        self.assertEqual(self.request_process(source).status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(Book.objects.exists())

    def test_unauthorized_user_is_blocked(self):
        source = self.create_source()
        self.client.force_authenticate(None)
        response = self.request_process(source)
        self.assertIn(response.status_code, {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN})
        self.assertFalse(Book.objects.exists())

    @patch("library.views.process_book.delay")
    @patch("library.tasks.generate_embeddings", return_value=[[0.1], [0.2]])
    @patch("library.tasks.extract_text_by_page", return_value=[(1, "conteudo da primeira pagina")])
    @patch("library.tasks.chunk_text", return_value=[
        {"chunk_index": 0, "page_number": 1, "content": "primeiro"},
        {"chunk_index": 1, "page_number": 1, "content": "segundo"},
    ])
    def test_catalog_source_reaches_book_and_chunks(self, chunk, extract, embeddings, delay):
        delay.return_value.id = "task-pipeline"
        source = self.create_source("pipeline.pdf")
        response = self.request_process(source)
        book = Book.objects.get(source=source)

        process_book.run(book.id)
        book.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(book.status, "ready")
        self.assertEqual(book.total_chunks, 2)
        self.assertEqual(BookChunk.objects.filter(book=book).count(), 2)
        extract.assert_called_once_with(book.file.path)
        embeddings.assert_called_once_with(["primeiro", "segundo"])

    @patch("library.tasks.extract_text_by_page")
    def test_task_is_idempotent_when_book_is_not_processing(self, extract):
        source = self.create_source("ready.pdf")
        book = Book.objects.create(source=source, title="Ready", file="books/ready.pdf", status="ready")
        result = process_book.run(book.id)
        self.assertTrue(result["skipped"])
        extract.assert_not_called()

    @patch("library.tasks.generate_embeddings", return_value=[])
    @patch("library.tasks.extract_text_by_page", return_value=[(1, "novo")])
    @patch("library.tasks.chunk_text", return_value=[{"chunk_index": 0, "page_number": 1, "content": "novo"}])
    def test_embedding_mismatch_preserves_existing_chunks(self, chunk, extract, embeddings):
        source = self.create_source("mismatch.pdf")
        book = Book.objects.create(source=source, title="Mismatch", file="books/mismatch.pdf", status="processing")
        prior = BookChunk.objects.create(book=book, chunk_index=0, page_number=1, content="anterior", embedding=[0.5])
        with self.assertRaises(ValueError):
            process_book.run(book.id)
        book.refresh_from_db()
        self.assertEqual(book.status, "error")
        self.assertTrue(BookChunk.objects.filter(pk=prior.pk, content="anterior").exists())
