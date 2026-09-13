from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITransactionTestCase

from library.models import Book, BookChunk


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class BookProcessingTests(APITransactionTestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="book_admin", email="book-admin@example.com", is_staff=True,
        )
        self.client.force_authenticate(self.admin)
        self.book = Book.objects.create(title="Livro", file="library/books/test.pdf")

    def request_process(self):
        return self.client.post(reverse("library-book-process", kwargs={"pk": self.book.pk}), {}, format="json", REMOTE_ADDR="127.0.0.1")

    @patch("library.views.process_book.delay")
    def test_enqueue_sees_committed_processing_state_and_preserves_contract(self, delay):
        def enqueue(book_id):
            self.assertFalse(connection.in_atomic_block)
            self.assertTrue(connection.get_autocommit())
            self.assertEqual(Book.objects.get(pk=book_id).status, "processing")
            return type("Result", (), {"id": "task-book"})()
        delay.side_effect = enqueue
        response = self.request_process()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data, {"book_id": self.book.pk, "task_id": "task-book", "status": "queued"})
        delay.assert_called_once_with(self.book.pk)

    @patch("library.views.process_book.delay")
    def test_outer_transaction_defers_enqueue_until_commit(self, delay):
        with transaction.atomic():
            self.assertEqual(self.request_process().status_code, 202)
            delay.assert_not_called()
        delay.assert_called_once_with(self.book.pk)

    @patch("library.views.process_book.delay")
    def test_rollback_discards_enqueue(self, delay):
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            with transaction.atomic():
                self.request_process()
                delay.assert_not_called()
                raise RuntimeError("rollback")
        delay.assert_not_called()
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, "uploaded")

    @patch("library.views.process_book.delay", side_effect=RuntimeError("private broker details"))
    def test_enqueue_failure_restores_status_without_leaking_details_or_losing_chunks(self, delay):
        chunk = BookChunk.objects.create(book=self.book, chunk_index=0, content="Preservar")
        for previous_status in ("uploaded", "ready", "error"):
            with self.subTest(previous_status=previous_status):
                previous_processed_at = timezone.now()
                Book.objects.filter(pk=self.book.pk).update(
                    status=previous_status,
                    progress_percent=100,
                    progress_stage="Concluído",
                    error_message="erro anterior",
                    processed_at=previous_processed_at,
                )
                with self.assertLogs("library.views", level="ERROR"):
                    response = self.request_process()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.data, {"detail": "Não foi possível acessar a fila de processamento."})
                self.book.refresh_from_db()
                self.assertEqual(self.book.status, previous_status)
                self.assertEqual(self.book.progress_percent, 100)
                self.assertEqual(self.book.progress_stage, "Concluído")
                self.assertEqual(self.book.error_message, "erro anterior")
                self.assertEqual(self.book.processed_at, previous_processed_at)
                self.assertTrue(BookChunk.objects.filter(pk=chunk.pk, content="Preservar").exists())

    @patch("library.views.process_book.delay")
    def test_failure_does_not_overwrite_worker_progress(self, delay):
        def enqueue(book_id):
            Book.objects.filter(pk=book_id).update(progress_percent=20, progress_stage="Extraindo conteúdo")
            raise RuntimeError("acknowledgement failed")
        delay.side_effect = enqueue
        with self.assertLogs("library.views", level="ERROR"):
            self.assertEqual(self.request_process().status_code, 503)
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, "processing")
        self.assertEqual(self.book.progress_percent, 20)
        self.assertEqual(self.book.progress_stage, "Extraindo conteúdo")

    @patch("library.views.process_book.delay")
    def test_repeated_request_does_not_enqueue_twice(self, delay):
        delay.return_value.id = "task-book"
        self.assertEqual(self.request_process().status_code, 202)
        self.assertEqual(self.request_process().status_code, 409)
        delay.assert_called_once_with(self.book.pk)

    @patch("library.views.process_book.delay")
    def test_non_admin_cannot_enqueue(self, delay):
        self.admin.is_staff = False
        self.admin.save(update_fields=["is_staff"])
        self.assertEqual(self.request_process().status_code, 403)
        delay.assert_not_called()
