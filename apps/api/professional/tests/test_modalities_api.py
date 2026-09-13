from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from professional.models import Opportunity, ProfessionalModality


class ModalityApiTests(APITestCase):
    modalities_url = "/api/professional/modalities/"
    opportunities_url = "/api/professional/opportunities/"

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner-pps2", email="owner-pps2@example.com", password="test-pass", is_staff=True)
        self.other = user_model.objects.create_user(username="other-pps2", email="other-pps2@example.com", password="test-pass", is_staff=True)
        self.web = ProfessionalModality.objects.get(slug="web-development")
        self.ai = ProfessionalModality.objects.get(slug="artificial-intelligence")
        self.analytics = ProfessionalModality.objects.get(slug="analytics")
        self.inactive = ProfessionalModality.objects.create(name="Inativa", slug="inactive-test", domain="OTHER", is_active=False, sort_order=999)
        self.payload = {"title": "Automação comercial", "description": "Briefing", "source": "DIRECT_CLIENT", "currency": "BRL"}

    def authenticate(self, user=None):
        self.client.force_authenticate(user or self.owner)

    def create_opportunity(self, user=None):
        return Opportunity.objects.create(created_by=user or self.owner, **self.payload)

    def test_active_catalog_is_consultable_and_inactive_is_hidden(self):
        self.authenticate()
        response = self.client.get(self.modalities_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [item["slug"] for item in response.data]
        self.assertIn("web-development", slugs)
        self.assertNotIn(self.inactive.slug, slugs)
        self.assertIn("domain", response.data[0])

    def test_creation_accepts_multiple_modalities_and_read_returns_details(self):
        self.authenticate()
        response = self.client.post(self.opportunities_url, {**self.payload, "modality_ids": [self.web.id, self.ai.id, self.analytics.id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual({item["slug"] for item in response.data["modalities"]}, {self.web.slug, self.ai.slug, self.analytics.slug})
        opportunity = Opportunity.objects.get(pk=response.data["id"])
        self.assertEqual(opportunity.modalities.count(), 3)

    def test_update_adds_and_removes_modalities(self):
        opportunity = self.create_opportunity()
        opportunity.modalities.set([self.web, self.ai])
        self.authenticate()
        detail = f"{self.opportunities_url}{opportunity.id}/"
        response = self.client.patch(detail, {"modality_ids": [self.ai.id, self.analytics.id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in response.data["modalities"]}, {self.ai.id, self.analytics.id})
        opportunity.refresh_from_db()
        self.assertEqual(set(opportunity.modalities.values_list("id", flat=True)), {self.ai.id, self.analytics.id})

    def test_unknown_and_inactive_ids_are_rejected(self):
        self.authenticate()
        for modality_id in [999999, self.inactive.id]:
            response = self.client.post(self.opportunities_url, {**self.payload, "modality_ids": [modality_id]}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("modality_ids", response.data)

    def test_duplicate_ids_do_not_create_duplicate_relations(self):
        self.authenticate()
        response = self.client.post(self.opportunities_url, {**self.payload, "modality_ids": [self.web.id, self.web.id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["modalities"]), 1)

    def test_isolation_remains_for_modality_changes(self):
        opportunity = self.create_opportunity(self.other)
        opportunity.modalities.add(self.web)
        self.authenticate(self.owner)
        detail = f"{self.opportunities_url}{opportunity.id}/"
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.patch(detail, {"modality_ids": [self.ai.id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        opportunity.refresh_from_db()
        self.assertEqual(list(opportunity.modalities.values_list("id", flat=True)), [self.web.id])

    def test_filter_returns_only_matching_owned_opportunities(self):
        web_opportunity = self.create_opportunity()
        web_opportunity.modalities.add(self.web)
        ai_opportunity = self.create_opportunity()
        ai_opportunity.modalities.add(self.ai)
        foreign = self.create_opportunity(self.other)
        foreign.modalities.add(self.web)
        self.authenticate()
        response = self.client.get(self.opportunities_url, {"modality": self.web.slug})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data["results"]], [web_opportunity.id])
