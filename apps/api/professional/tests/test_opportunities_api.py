from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from professional.models import Opportunity


class OpportunityApiTests(APITestCase):
    url = "/api/professional/opportunities/"

    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="owner", email="owner@example.com", password="safe-test-pass", is_staff=True)
        self.other = user_model.objects.create_user(username="other", email="other@example.com", password="safe-test-pass", is_staff=True)
        self.payload = {"title": "Dashboard executivo", "description": "Briefing do cliente", "source": "WORKANA", "currency": "brl", "budget_min": "1000.00", "budget_max": "2500.00"}

    def create_opportunity(self, user=None, **overrides):
        data = {"created_by": user or self.owner, "title": "Projeto", "description": "Descrição", "source": Opportunity.Source.DIRECT_CLIENT, "currency": "BRL"}
        data.update(overrides)
        return Opportunity.objects.create(**data)

    def test_authenticated_user_creates_and_server_sets_owner(self):
        self.client.force_authenticate(self.owner)
        payload = {**self.payload, "created_by": self.other.pk}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunity.objects.get(pk=response.data["id"])
        self.assertEqual(opportunity.created_by, self.owner)
        self.assertEqual(opportunity.currency, "BRL")

    def test_unauthenticated_user_is_rejected(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.url, self.payload, format="json").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_contains_only_current_users_opportunities(self):
        mine = self.create_opportunity()
        self.create_opportunity(self.other, title="Não deve aparecer")
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data["results"]], [mine.id])

    def test_owner_can_retrieve_update_and_delete(self):
        opportunity = self.create_opportunity()
        self.client.force_authenticate(self.owner)
        detail = f"{self.url}{opportunity.pk}/"
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_200_OK)
        response = self.client.patch(detail, {"title": "Atualizado"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.title, "Atualizado")
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Opportunity.objects.filter(pk=opportunity.pk).exists())

    def test_other_users_object_is_hidden_for_all_detail_actions(self):
        opportunity = self.create_opportunity(self.other)
        self.client.force_authenticate(self.owner)
        detail = f"{self.url}{opportunity.pk}/"
        self.assertEqual(self.client.get(detail).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(detail, {"title": "Inválido"}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_404_NOT_FOUND)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.title, "Projeto")

    def test_budget_and_currency_validations(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, {**self.payload, "budget_min": "3000", "budget_max": "2000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("budget_max", response.data)
        response = self.client.post(self.url, {**self.payload, "budget_min": "-1"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("budget_min", response.data)
        response = self.client.post(self.url, {**self.payload, "currency": "REAL"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("currency", response.data)

    def test_optional_fields_and_status_are_persisted(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, {**self.payload, "source_url": "https://example.com/job", "client_name": "Cliente", "deadline": "2026-10-10", "proposal_deadline": "2026-09-30", "status": "ANALYZING", "notes": "Contato inicial"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunity.objects.get(pk=response.data["id"])
        self.assertEqual(opportunity.budget_min, Decimal("1000.00"))
        self.assertEqual(opportunity.status, Opportunity.Status.ANALYZING)
