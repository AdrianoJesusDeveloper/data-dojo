import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import Book, LibrarySource, ModernizationPlan, StudioProject


@override_settings(
    DDJ_CONTENT_STUDIO_ENABLED=True,
    DDJ_CONTENT_STUDIO_LOCAL_ONLY=True,
)
class LibraryApiSecurityTests(APITestCase):
    def setUp(self):
        users = get_user_model().objects
        self.user = users.create_user(
            email="student-library@example.com",
            username="student_library",
            password="dojo-test-password",
        )
        self.admin = users.create_user(
            email="admin-library@example.com",
            username="admin_library",
            password="dojo-test-password",
            is_staff=True,
        )
        self.other_admin = users.create_user(
            email="other-admin-library@example.com",
            username="other_admin_library",
            password="dojo-test-password",
            is_staff=True,
        )

    @staticmethod
    def protected_requests():
        return (
            ("get", reverse("library-studio-status"), None),
            ("post", reverse("library-studio-scan"), {}),
            ("get", reverse("library-source-list"), None),
            ("get", reverse("library-studio-projects"), None),
            ("post", reverse("library-studio-projects"), {"title": "Projeto", "theme": "Tema", "objective": "Objetivo"}),
            ("get", reverse("library-studio-project-detail", kwargs={"pk": 999999}), None),
            ("post", reverse("library-studio-generate-plan", kwargs={"pk": 999999}), {}),
            ("post", reverse("library-studio-approve", kwargs={"pk": 999999}), {"decision": "approved"}),
            ("post", reverse("library-studio-generate-content", kwargs={"pk": 999999}), {}),
            ("put", reverse("library-studio-plan-edit", kwargs={"pk": 999999}), {"plan": {}}),
            ("get", reverse("library-studio-plan-versions", kwargs={"pk": 999999}), None),
            ("post", reverse("library-studio-comments", kwargs={"pk": 999999}), {"text": "Teste"}),
            ("post", reverse("library-studio-comment-resolve", kwargs={"pk": 999999, "comment_pk": 999999}), {}),
            ("post", reverse("library-studio-archive", kwargs={"pk": 999999}), {"archived": True}),
            ("delete", reverse("library-studio-permanent-delete", kwargs={"pk": 999999}), {"confirmation": "EXCLUIR DEFINITIVAMENTE"}),
            ("get", reverse("library-book-upload"), None),
            ("post", reverse("library-book-upload"), {}),
            ("post", reverse("library-book-process", kwargs={"pk": 999999}), {}),
            ("get", reverse("library-book-status", kwargs={"pk": 999999}), None),
            ("get", reverse("library-trilha-list"), None),
            ("post", reverse("library-script-generate"), {}),
            ("get", reverse("library-script-list"), None),
            ("get", reverse("library-script-detail", kwargs={"pk": 999999}), None),
        )

    def request(self, method, url, data=None, remote_addr="127.0.0.1"):
        return getattr(self.client, method)(
            url,
            data=data,
            format="json" if data is not None else None,
            REMOTE_ADDR=remote_addr,
        )

    def test_anonymous_user_cannot_access_private_library_endpoints(self):
        for method, url, data in self.protected_requests():
            with self.subTest(method=method, url=url):
                response = self.request(method, url, data)
                self.assertIn(response.status_code, {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN})

    def test_authenticated_non_staff_user_cannot_access_admin_endpoints(self):
        self.client.force_authenticate(self.user)
        for method, url, data in self.protected_requests():
            with self.subTest(method=method, url=url):
                response = self.request(method, url, data)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_access_local_studio_when_enabled(self):
        self.client.force_authenticate(self.admin)
        response = self.request("get", reverse("library-studio-status"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["enabled"])
        self.assertTrue(response.data["local_only"])

    @override_settings(DDJ_CONTENT_STUDIO_ENABLED=False)
    def test_studio_fails_closed_when_feature_flag_is_disabled(self):
        self.client.force_authenticate(self.admin)
        response = self.request("get", reverse("library-studio-status"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_local_only_studio_rejects_non_loopback_request(self):
        self.client.force_authenticate(self.admin)
        response = self.request(
            "get", reverse("library-studio-status"), remote_addr="203.0.113.10"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        ENVIRONMENT="production",
        DDJ_CONTENT_STUDIO_ENABLED=False,
    )
    def test_production_configuration_keeps_studio_blocked(self):
        self.client.force_authenticate(self.admin)
        response = self.request("get", reverse("library-studio-status"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_status_does_not_expose_paths_or_sensitive_settings(self):
        self.client.force_authenticate(self.admin)
        response = self.request("get", reverse("library-studio-status"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("library_path", response.data)
        payload = json.dumps(response.data).upper()
        for sensitive_name in ("SECRET", "PASSWORD", "API_KEY", "TOKEN", "C:\\"):
            self.assertNotIn(sensitive_name, payload)

    def test_book_status_sanitizes_internal_processing_error(self):
        book = Book.objects.create(
            title="Falha privada",
            file="library/books/falha.pdf",
            status="error",
            error_message="PermissionError em C:\\private\\books\\falha.pdf API_KEY=secret",
        )
        self.client.force_authenticate(self.admin)
        response = self.request(
            "get", reverse("library-book-status", kwargs={"pk": book.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = json.dumps(response.data)
        self.assertNotIn("C:\\private", payload)
        self.assertNotIn("API_KEY", payload)
        self.assertIn("Consulte os logs", response.data["error_message"])

    def test_scan_and_catalog_expose_only_paths_relative_to_private_root(self):
        self.client.force_authenticate(self.admin)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "trilha-privada"
            nested.mkdir()
            (nested / "livro.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
            with self.settings(LOCAL_LIBRARY_PATH=root):
                scan = self.request("post", reverse("library-studio-scan"), {})
                sources = self.request("get", reverse("library-source-list"))

        self.assertEqual(scan.status_code, status.HTTP_200_OK)
        self.assertNotIn("root", scan.data)
        self.assertNotIn(str(root), json.dumps(scan.data))
        self.assertEqual(sources.status_code, status.HTTP_200_OK)
        source = sources.data["results"][0]
        self.assertEqual(source["relative_path"], "trilha-privada/livro.pdf")
        self.assertNotIn(str(root), json.dumps(source))

    def test_scan_error_does_not_expose_missing_absolute_path(self):
        self.client.force_authenticate(self.admin)
        private_path = Path("C:/private/not-present/sensei-library")
        with self.settings(LOCAL_LIBRARY_PATH=private_path):
            response = self.request("post", reverse("library-studio-scan"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn(str(private_path), response.data["detail"])

    def test_only_staff_can_create_project_and_creator_is_server_controlled(self):
        payload = {"title": "Projeto seguro", "theme": "RAG", "objective": "Ensinar com fontes"}
        self.client.force_authenticate(self.user)
        denied = self.request("post", reverse("library-studio-projects"), payload)
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        created = self.request("post", reverse("library-studio-projects"), payload)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        project = StudioProject.objects.get(pk=created.data["id"])
        self.assertEqual(project.created_by, self.admin)

    def test_project_with_processed_book_persists_its_catalog_source(self):
        source = LibrarySource.objects.create(
            relative_path="series/livro.pdf",
            filename="livro.pdf",
            extension="pdf",
            sha256="source-project",
            status="supported",
        )
        book = Book.objects.create(
            title="Séries temporais",
            file="library/books/livro.pdf",
            status="ready",
            source=source,
        )
        self.client.force_authenticate(self.admin)

        response = self.request(
            "post",
            reverse("library-studio-projects"),
            {
                "title": "Projeto com fonte",
                "theme": "Séries temporais",
                "objective": "Ensinar fundamentos",
                "source": source.id,
                "books": [book.id],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        project = StudioProject.objects.get(pk=response.data["id"])
        self.assertEqual(project.source_id, source.id)
        self.assertEqual(list(project.books.values_list("id", flat=True)), [book.id])

    def test_other_staff_user_cannot_read_update_or_run_owner_workflow(self):
        project = StudioProject.objects.create(
            title="Privado", theme="Tema", objective="Objetivo", created_by=self.admin
        )
        self.client.force_authenticate(self.other_admin)
        requests = (
            ("get", reverse("library-studio-project-detail", kwargs={"pk": project.pk}), None),
            ("patch", reverse("library-studio-project-detail", kwargs={"pk": project.pk}), {"title": "Ataque"}),
            ("post", reverse("library-studio-generate-plan", kwargs={"pk": project.pk}), {}),
            ("post", reverse("library-studio-approve", kwargs={"pk": project.pk}), {"decision": "approved"}),
            ("post", reverse("library-studio-generate-content", kwargs={"pk": project.pk}), {}),
        )
        for method, url, data in requests:
            with self.subTest(method=method, url=url):
                self.assertEqual(self.request(method, url, data).status_code, status.HTTP_404_NOT_FOUND)
        project.refresh_from_db()
        self.assertEqual(project.title, "Privado")

    def test_missing_object_ids_return_not_found_for_owner_actions(self):
        self.client.force_authenticate(self.admin)
        requests = (
            ("get", reverse("library-studio-project-detail", kwargs={"pk": 999999})),
            ("post", reverse("library-studio-generate-plan", kwargs={"pk": 999999})),
            ("post", reverse("library-studio-approve", kwargs={"pk": 999999})),
            ("post", reverse("library-studio-generate-content", kwargs={"pk": 999999})),
            ("post", reverse("library-book-process", kwargs={"pk": 999999})),
            ("get", reverse("library-book-status", kwargs={"pk": 999999})),
            ("get", reverse("library-script-detail", kwargs={"pk": 999999})),
        )
        for method, url in requests:
            with self.subTest(method=method, url=url):
                response = self.request(method, url, {}) if method == "post" else self.request(method, url)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authorized_owner_reaches_generate_plan_validation(self):
        project = StudioProject.objects.create(
            title="Sem livros", theme="Tema", objective="Objetivo", created_by=self.admin
        )
        self.client.force_authenticate(self.admin)
        response = self.request(
            "post", reverse("library-studio-generate-plan", kwargs={"pk": project.pk}), {}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("livro", response.data["detail"].lower())

    def test_generation_and_approval_require_authorized_staff(self):
        project = StudioProject.objects.create(
            title="Workflow", theme="Tema", objective="Objetivo", created_by=self.admin
        )
        ModernizationPlan.objects.create(project=project, status="approved")
        self.client.force_authenticate(self.user)
        for name in ("library-studio-generate-plan", "library-studio-approve", "library-studio-generate-content"):
            with self.subTest(name=name):
                response = self.request("post", reverse(name, kwargs={"pk": project.pk}), {"decision": "approved"})
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("library.views.generate_content_item")
    def test_authorized_owner_can_approve_and_generate_content(self, generate_content):
        project = StudioProject.objects.create(
            title="Workflow", theme="Tema", objective="Objetivo", created_by=self.admin
        )
        ModernizationPlan.objects.create(project=project, status="review", proposed_architecture={"modules": [{"title": "MÃ³dulo", "lessons": [{"title": "Aula"}]}]})
        self.client.force_authenticate(self.admin)
        approval = self.request(
            "post",
            reverse("library-studio-approve", kwargs={"pk": project.pk}),
            {"decision": "approved", "notes": "Revisado"},
        )
        self.assertEqual(approval.status_code, status.HTTP_200_OK)

        generate_content.return_value = ({"objective": "ConteÃºdo seguro"}, "raw-private-provider-response")
        content = self.request(
            "post", reverse("library-studio-generate-content", kwargs={"pk": project.pk}), {"target_type": "lesson", "target_index": 0}
        )
        self.assertEqual(content.status_code, status.HTTP_200_OK)
        self.assertNotIn("raw_response", content.data)
        self.assertNotIn("raw-private-provider-response", json.dumps(content.data))

    @patch("library.views.generate_content_item")
    def test_provider_failure_does_not_expose_secret_or_server_path(self, generate_content):
        project = StudioProject.objects.create(
            title="Workflow", theme="Tema", objective="Objetivo", created_by=self.admin
        )
        ModernizationPlan.objects.create(project=project, status="approved", proposed_architecture={"modules": [{"title": "MÃ³dulo", "lessons": [{"title": "Aula"}]}]})
        generate_content.side_effect = RuntimeError(
            "OPENAI_API_KEY=private em C:\\private\\provider.json"
        )
        self.client.force_authenticate(self.admin)
        response = self.request(
            "post", reverse("library-studio-generate-content", kwargs={"pk": project.pk}), {"target_type": "lesson", "target_index": 0}
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        payload = json.dumps(response.data)
        self.assertNotIn("OPENAI_API_KEY", payload)
        self.assertNotIn("C:\\private", payload)
