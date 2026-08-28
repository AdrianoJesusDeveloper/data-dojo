from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import LibrarySource


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class LibrarySourcePaginationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(
            email="catalog-admin@example.com", username="catalog_admin", password="test", is_staff=True
        )
        LibrarySource.objects.bulk_create([
            LibrarySource(
                relative_path=f"area/livro-{index:03d}.pdf",
                filename=f"livro-{index:03d}.pdf",
                extension="pdf",
                size_bytes=index,
                status="supported",
            )
            for index in range(1, 204)
        ])

    def setUp(self):
        self.client.force_authenticate(self.admin)
        self.url = reverse("library-source-list")

    def test_default_page_has_25_items_and_reports_total(self):
        response = self.client.get(self.url, REMOTE_ADDR="127.0.0.1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 203)
        self.assertEqual(len(response.data["results"]), 25)
        self.assertIsNone(response.data["previous"])
        self.assertIsNotNone(response.data["next"])

    def test_next_previous_and_last_page_are_reachable(self):
        second = self.client.get(self.url, {"page": 2}, REMOTE_ADDR="127.0.0.1")
        self.assertIsNotNone(second.data["previous"])
        self.assertIsNotNone(second.data["next"])
        last = self.client.get(self.url, {"page": 9}, REMOTE_ADDR="127.0.0.1")
        self.assertEqual(len(last.data["results"]), 3)
        self.assertEqual(last.data["results"][-1]["filename"], "livro-203.pdf")
        self.assertIsNone(last.data["next"])

    def test_page_size_is_configurable_and_capped(self):
        fifty = self.client.get(self.url, {"page_size": 50}, REMOTE_ADDR="127.0.0.1")
        self.assertEqual(len(fifty.data["results"]), 50)
        capped = self.client.get(self.url, {"page_size": 1000}, REMOTE_ADDR="127.0.0.1")
        self.assertEqual(len(capped.data["results"]), 100)

    def test_search_runs_before_pagination_across_entire_catalog(self):
        response = self.client.get(self.url, {"search": "livro-203"}, REMOTE_ADDR="127.0.0.1")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["filename"], "livro-203.pdf")
