from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class ProfessionalAdminAccessTests(APITestCase):
    opportunities_url = "/api/professional/opportunities/"
    modalities_url = "/api/professional/modalities/"

    def setUp(self):
        users = get_user_model().objects
        self.student = users.create_user(
            username="professional-student",
            email="professional-student@example.com",
            password="test-pass",
        )
        self.staff = users.create_user(
            username="professional-staff",
            email="professional-staff@example.com",
            password="test-pass",
            is_staff=True,
        )
        self.superuser = users.create_user(
            username="professional-superuser",
            email="professional-superuser@example.com",
            password="test-pass",
            is_superuser=True,
            is_staff=False,
        )

    def test_student_is_forbidden_from_all_professional_roots(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(self.opportunities_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self.modalities_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post(self.opportunities_url, {"title": "Bloqueado"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_staff_and_superuser_keep_access(self):
        for user in (self.staff, self.superuser):
            with self.subTest(user=user.email):
                self.client.force_authenticate(user)
                self.assertEqual(self.client.get(self.opportunities_url).status_code, status.HTTP_200_OK)
                self.assertEqual(self.client.get(self.modalities_url).status_code, status.HTTP_200_OK)
