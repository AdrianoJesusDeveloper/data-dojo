import io
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import Book, BookSection, MediaAsset, ReadingMark, ReadingProgress


class LibraryReaderMediaTests(APITestCase):
    def setUp(self):
        users = get_user_model().objects

        self.admin = users.create_user(
            email="reader-admin@example.com",
            username="reader_admin",
            password="dojo-test-password",
            is_staff=True,
        )
        self.other_admin = users.create_user(
            email="reader-other@example.com",
            username="reader_other",
            password="dojo-test-password",
            is_staff=True,
        )
        self.student = users.create_user(
            email="reader-student@example.com",
            username="reader_student",
            password="dojo-test-password",
        )

        self.client.force_authenticate(self.admin)

        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

        self.media_root = Path(self.temporary.name) / "media"
        self.media_root.mkdir(parents=True)

        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_root,
            DDJ_CONTENT_STUDIO_ENABLED=True,
            DDJ_CONTENT_STUDIO_LOCAL_ONLY=True,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def request(self, method, url, data=None, format=None, **extra):
        extra.setdefault("REMOTE_ADDR", "127.0.0.1")
        return getattr(self.client, method)(
            url,
            data=data,
            format=format,
            **extra,
        )

    def create_book(self, name="livro.txt", content=b"conteudo do livro", **overrides):
        relative = Path("library/books") / name
        physical = self.media_root / relative
        physical.parent.mkdir(parents=True, exist_ok=True)
        physical.write_bytes(content)

        values = {
            "title": Path(name).stem,
            "author": "Autor Teste",
            "file": relative.as_posix(),
            "status": "ready",
            "lifecycle": "active",
        }
        values.update(overrides)
        return Book.objects.create(**values)

    def create_section(self, book, position=1, text="Python para análise de dados"):
        return BookSection.objects.create(
            book=book,
            position=position,
            location=f"section:{position}",
            title=f"Seção {position}",
            text=text,
            html=f"<p>{text}</p>",
        )

    @staticmethod
    def png_upload(name="capa.png"):
        buffer = io.BytesIO()
        Image.new("RGB", (32, 48), "white").save(buffer, format="PNG")
        return SimpleUploadedFile(
            name,
            buffer.getvalue(),
            content_type="image/png",
        )

    def test_reader_metadata_builds_txt_sections(self):
        book = self.create_book(
            "reader.txt",
            b"Primeiro conteudo seguro para o leitor.",
        )

        response = self.request(
            "get",
            reverse("library-reader", kwargs={"pk": book.pk}),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["book"]["id"], book.pk)
        self.assertEqual(response.data["book"]["format"], "txt")
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(len(response.data["toc"]), 1)
        self.assertTrue(
            BookSection.objects.filter(book=book, position=1).exists()
        )

        section = self.request(
            "get",
            reverse(
                "library-reader-section",
                kwargs={"pk": book.pk, "position": 1},
            ),
        )

        self.assertEqual(section.status_code, status.HTTP_200_OK)
        self.assertIn("Primeiro conteudo", section.data["text"])

    def test_pdf_file_supports_http_range(self):
        payload = b"%PDF-1.4\nconteudo-pdf-teste\n%%EOF"
        book = self.create_book("range.pdf", payload)

        response = self.request(
            "get",
            reverse("library-reader-file", kwargs={"pk": book.pk}),
            HTTP_RANGE="bytes=0-3",
        )

        self.assertEqual(response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertTrue(response["Content-Range"].startswith("bytes 0-3/"))
        self.assertEqual(b"".join(response.streaming_content), b"%PDF")

    def test_progress_is_persisted_and_isolated_per_user(self):
        book = self.create_book()
        self.create_section(book)

        response = self.request(
            "put",
            reverse("library-reader-progress", kwargs={"pk": book.pk}),
            {
                "position": 1,
                "offset": 0.5,
                "progress_percentage": 50,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["position"], 1)
        self.assertEqual(response.data["location"], "section:1")
        self.assertEqual(
            ReadingProgress.objects.filter(
                book=book,
                user=self.admin,
            ).count(),
            1,
        )

        self.client.force_authenticate(self.other_admin)

        other = self.request(
            "get",
            reverse("library-reader-progress", kwargs={"pk": book.pk}),
        )

        self.assertEqual(other.status_code, status.HTTP_200_OK)
        self.assertEqual(other.data, {})

    def test_bookmarks_annotations_and_highlights_are_private(self):
        book = self.create_book()
        self.create_section(book)

        bookmark = self.request(
            "post",
            reverse("library-reader-marks", kwargs={"pk": book.pk}),
            {
                "kind": "bookmark",
                "position": 1,
                "offset": 0,
                "note": "Voltar aqui",
            },
            format="json",
        )
        self.assertEqual(bookmark.status_code, status.HTTP_201_CREATED)

        annotation = self.request(
            "post",
            reverse("library-reader-marks", kwargs={"pk": book.pk}),
            {
                "kind": "annotation",
                "position": 1,
                "offset": 0.2,
                "note": "Minha anotação",
            },
            format="json",
        )
        self.assertEqual(annotation.status_code, status.HTTP_201_CREATED)

        highlight = self.request(
            "post",
            reverse("library-reader-marks", kwargs={"pk": book.pk}),
            {
                "kind": "highlight",
                "position": 1,
                "offset": 0.3,
                "selected_text": "Python",
                "start_offset": 0,
                "end_offset": 6,
                "note": "",
            },
            format="json",
        )
        self.assertEqual(highlight.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            ReadingMark.objects.filter(book=book, user=self.admin).count(),
            3,
        )

        self.client.force_authenticate(self.other_admin)

        listing = self.request(
            "get",
            reverse("library-reader-marks", kwargs={"pk": book.pk}),
        )
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 0)

        foreign = self.request(
            "patch",
            reverse(
                "library-reader-mark",
                kwargs={
                    "pk": book.pk,
                    "mark_pk": bookmark.data["id"],
                },
            ),
            {"note": "Tentativa externa"},
            format="json",
        )
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_annotation_and_highlight_are_rejected(self):
        book = self.create_book()
        self.create_section(book)

        annotation = self.request(
            "post",
            reverse("library-reader-marks", kwargs={"pk": book.pk}),
            {
                "kind": "annotation",
                "position": 1,
                "note": "",
            },
            format="json",
        )

        highlight = self.request(
            "post",
            reverse("library-reader-marks", kwargs={"pk": book.pk}),
            {
                "kind": "highlight",
                "position": 1,
                "selected_text": "",
            },
            format="json",
        )

        self.assertEqual(annotation.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(highlight.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ReadingMark.objects.filter(book=book).exists())

    def test_search_returns_matching_sections(self):
        book = self.create_book()
        self.create_section(
            book,
            1,
            "Python e Pandas para análise de dados.",
        )
        self.create_section(
            book,
            2,
            "SQL para consultas relacionais.",
        )

        response = self.request(
            "get",
            reverse("library-reader-search", kwargs={"pk": book.pk}) + "?q=Python",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["position"], 1)
        self.assertIn("Python", response.data["results"][0]["snippet"])

        short = self.request(
            "get",
            reverse("library-reader-search", kwargs={"pk": book.pk}) + "?q=P",
        )

        self.assertEqual(short.status_code, status.HTTP_200_OK)
        self.assertEqual(short.data["count"], 0)

    def test_media_upload_deduplicates_by_sha256(self):
        first = self.request(
            "post",
            reverse("library-media"),
            {
                "file": self.png_upload("primeira.png"),
                "category": "BOOK_COVER",
                "title": "Capa",
            },
            format="multipart",
        )

        second = self.request(
            "post",
            reverse("library-media"),
            {
                "file": self.png_upload("segunda.png"),
                "category": "BOOK_COVER",
                "title": "Outra capa",
            },
            format="multipart",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(MediaAsset.objects.count(), 1)

    def test_book_upload_rejects_duplicate_content(self):
        first_file = SimpleUploadedFile(
            "primeiro.txt",
            b"mesmo conteudo",
            content_type="text/plain",
        )
        second_file = SimpleUploadedFile(
            "segundo.txt",
            b"mesmo conteudo",
            content_type="text/plain",
        )

        first = self.request(
            "post",
            reverse("library-book-upload"),
            {
                "title": "Primeiro livro",
                "file": first_file,
            },
            format="multipart",
        )

        second = self.request(
            "post",
            reverse("library-book-upload"),
            {
                "title": "Livro duplicado",
                "file": second_file,
            },
            format="multipart",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Book.objects.count(), 1)

    def test_catalog_lifecycle_and_favorites(self):
        active = self.create_book(
            "active.txt",
            b"ativo",
            title="Livro Ativo",
            is_favorite=True,
        )
        archived = self.create_book(
            "archived.txt",
            b"arquivado",
            title="Livro Arquivado",
            lifecycle="archived",
        )

        default = self.request("get", reverse("library-visual-books"))
        self.assertEqual(default.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in default.data["results"]}
        self.assertIn(active.pk, ids)
        self.assertNotIn(archived.pk, ids)

        all_books = self.request(
            "get",
            reverse("library-visual-books") + "?lifecycle=all",
        )
        ids = {item["id"] for item in all_books.data["results"]}
        self.assertIn(active.pk, ids)
        self.assertIn(archived.pk, ids)

        favorites = self.request(
            "get",
            reverse("library-visual-books") + "?favorite=true",
        )
        ids = {item["id"] for item in favorites.data["results"]}
        self.assertEqual(ids, {active.pk})

    def test_reader_and_media_endpoints_require_staff(self):
        book = self.create_book()
        self.create_section(book)

        endpoints = (
            reverse("library-visual-books"),
            reverse("library-media"),
            reverse("library-reader", kwargs={"pk": book.pk}),
            reverse("library-reader-progress", kwargs={"pk": book.pk}),
            reverse("library-reader-marks", kwargs={"pk": book.pk}),
            reverse("library-reader-search", kwargs={"pk": book.pk}) + "?q=Python",
        )

        self.client.force_authenticate(None)
        for url in endpoints:
            with self.subTest(mode="anonymous", url=url):
                response = self.request("get", url)
                self.assertIn(
                    response.status_code,
                    {
                        status.HTTP_401_UNAUTHORIZED,
                        status.HTTP_403_FORBIDDEN,
                    },
                )

        self.client.force_authenticate(self.student)
        for url in endpoints:
            with self.subTest(mode="student", url=url):
                response = self.request("get", url)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )