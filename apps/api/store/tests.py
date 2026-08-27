from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AffiliateClick, AffiliateOffer, Cart, Category, CommercePartner, DropshipOffer, Order, Payment, Product, ProductQuestion, ProductReview, SupplierFulfillment, validate_product_image_size


class StoreApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="samurai@example.com", username="samurai", password="dojo-test-password"
        )
        self.category = Category.objects.create(name="Livros", slug="livros", active=True)
        self.product = Product.objects.create(
            category=self.category,
            name="Livro Python",
            slug="livro-python",
            product_type="physical",
            price="50.00",
            stock=3,
            active=True,
        )

    def test_catalog_is_public_but_cart_requires_authentication(self):
        catalog = self.client.get(reverse("store-products"))
        cart = self.client.get(reverse("store-cart"))

        self.assertEqual(catalog.status_code, status.HTTP_200_OK)
        self.assertIn("Livro Python", [product["name"] for product in catalog.data["results"]])
        self.assertEqual(cart.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_catalog_exposes_product_image_and_video_urls(self):
        self.product.image_url = "https://cdn.example.com/produto.webp"
        self.product.video_url = "https://www.youtube.com/watch?v=video123"
        self.product.save(update_fields=["image_url", "video_url"])

        catalog = self.client.get(reverse("store-products"))
        product_data = next(item for item in catalog.data["results"] if item["id"] == self.product.id)

        self.assertEqual(product_data["image_url"], self.product.image_url)
        self.assertEqual(product_data["video_url"], self.product.video_url)

    def test_product_image_upload_rejects_files_above_five_megabytes(self):
        oversized = SimpleUploadedFile("produto.webp", b"0" * (5 * 1024 * 1024 + 1), content_type="image/webp")

        with self.assertRaisesMessage(ValidationError, "A imagem deve ter no máximo 5 MB."):
            validate_product_image_size(oversized)

    def test_catalog_query_count_does_not_grow_per_product(self):
        for index in range(5):
            Product.objects.create(
                category=self.category,
                name=f"Produto escalável {index}",
                slug=f"produto-escalavel-{index}",
                product_type="digital",
                price="10.00",
                active=True,
            )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("store-products"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(queries), 3)

    def test_catalog_filters_by_search_category_product_type_and_sales_model(self):
        service = Product.objects.create(
            category=self.category,
            name="Mentoria de Analytics",
            slug="mentoria-analytics",
            short_description="Orientação para carreira em dados",
            product_type="service",
            sales_model="own",
            price="120.00",
            active=True,
        )

        search = self.client.get(reverse("store-products"), {"search": "carreira"})
        combined = self.client.get(
            reverse("store-products"),
            {"category": "livros", "product_type": "service", "sales_model": "own"},
        )
        unfiltered = self.client.get(reverse("store-products"))
        invalid = self.client.get(reverse("store-products"), {"product_type": "invalido"})

        self.assertEqual([item["id"] for item in search.data["results"]], [service.id])
        self.assertEqual([item["id"] for item in combined.data["results"]], [service.id])
        self.assertEqual(
            [item["id"] for item in invalid.data["results"]],
            [item["id"] for item in unfiltered.data["results"]],
        )

    def test_cart_rejects_quantity_above_stock(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 4}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Cart.objects.filter(user=self.user, items__isnull=False).exists())

    def test_checkout_creates_order_payment_and_reduces_stock(self):
        self.client.force_authenticate(self.user)
        add = self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 2}, format="json"
        )
        checkout = self.client.post(reverse("store-checkout"), {"provider": "mercado_pago"}, format="json")

        self.assertEqual(add.status_code, status.HTTP_201_CREATED)
        self.assertEqual(checkout.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(user=self.user)
        self.assertEqual(str(order.total), "100.00")
        self.assertEqual(order.payment.provider, "mercado_pago")
        self.assertTrue(order.payment.external_id.startswith("sandbox_"))
        self.assertTrue(checkout.data["payment"]["sandbox"])
        self.assertIn(f"/sandbox/orders/{order.id}/approve/", checkout.data["payment"]["checkout_url"])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertFalse(Cart.objects.get(user=self.user).items.exists())

    def test_user_cannot_change_another_users_cart_item(self):
        self.client.force_authenticate(self.user)
        cart = self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 1}, format="json"
        ).data
        item_id = cart["items"][0]["id"]
        other = get_user_model().objects.create_user(
            email="other@example.com", username="other", password="dojo-test-password"
        )
        self.client.force_authenticate(other)

        response = self.client.patch(
            reverse("store-cart-item", kwargs={"pk": item_id}), {"quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_remove_item_and_receives_updated_cart(self):
        self.client.force_authenticate(self.user)
        cart = self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 2}, format="json"
        ).data

        response = self.client.delete(reverse("store-cart-item", kwargs={"pk": cart["items"][0]["id"]}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total"], "0.00")
        self.assertFalse(Cart.objects.get(user=self.user).items.exists())

    def test_authenticated_user_can_ask_question(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("store-product-questions", kwargs={"product_id": self.product.id}),
            {"question": "Este livro inclui exercícios práticos?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "samurai")
        self.assertTrue(ProductQuestion.objects.filter(product=self.product, user=self.user).exists())

    def test_questions_and_reviews_are_public_but_creation_requires_authentication(self):
        questions_url = reverse("store-product-questions", kwargs={"product_id": self.product.id})
        reviews_url = reverse("store-product-reviews", kwargs={"product_id": self.product.id})

        self.assertEqual(self.client.get(questions_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reviews_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(questions_url, {"question": "Dúvida"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reviews_url, {"rating": 5, "comment": "Ótimo"}).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_review_product_only_once_and_rating_is_aggregated(self):
        self.client.force_authenticate(self.user)
        url = reverse("store-product-reviews", kwargs={"product_id": self.product.id})

        first = self.client.post(url, {"rating": 5, "comment": "Excelente material."}, format="json")
        duplicate = self.client.post(url, {"rating": 4, "comment": "Outra avaliação."}, format="json")
        catalog = self.client.get(reverse("store-products"))
        product_data = next(item for item in catalog.data["results"] if item["id"] == self.product.id)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ProductReview.objects.filter(product=self.product, user=self.user).count(), 1)
        self.assertEqual(product_data["rating_average"], 5.0)
        self.assertEqual(product_data["reviews_count"], 1)

    def test_review_validates_rating_range(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("store-product-reviews", kwargs={"product_id": self.product.id}),
            {"rating": 6, "comment": "Nota inválida"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_can_cancel_cart_before_checkout(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 2}, format="json"
        )

        response = self.client.delete(reverse("store-cart"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total"], "0.00")

    def test_user_can_cancel_pending_order_and_stock_is_restored(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 2}, format="json"
        )
        order_data = self.client.post(
            reverse("store-checkout"), {"provider": "mercado_pago"}, format="json"
        ).data
        self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 1}, format="json"
        )

        response = self.client.post(reverse("store-order-cancel", kwargs={"pk": order_data["id"]}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "cancelled")
        self.assertEqual(response.data["payment"]["status"], "cancelled")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(Cart.objects.get(user=self.user).items.exists())
        self.assertTrue(Order.objects.filter(pk=order_data["id"], status="cancelled").exists())
        recent_orders = self.client.get(reverse("store-orders"))
        self.assertFalse(
            any(order["id"] == order_data["id"] for order in recent_orders.data["results"])
        )

    def test_sandbox_payment_can_be_approved_only_by_order_owner(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 1}, format="json"
        )
        order_data = self.client.post(
            reverse("store-checkout"), {"provider": "mercado_pago"}, format="json"
        ).data

        other = get_user_model().objects.create_user(
            email="sandbox-other@example.com", username="sandbox_other", password="dojo-test-password"
        )
        self.client.force_authenticate(other)
        denied = self.client.post(
            reverse("store-sandbox-payment-approve", kwargs={"pk": order_data["id"]})
        )
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.user)
        approved = self.client.post(
            reverse("store-sandbox-payment-approve", kwargs={"pk": order_data["id"]})
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(approved.data["status"], "paid")
        self.assertEqual(approved.data["payment"]["status"], "approved")

    @override_settings(PAYMENT_BACKEND="disabled")
    def test_checkout_fails_closed_when_payment_backend_is_disabled(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 1}, format="json"
        )

        response = self.client.post(
            reverse("store-checkout"), {"provider": "mercado_pago"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(Order.objects.filter(user=self.user).exists())
        self.assertFalse(Payment.objects.exists())

    def test_cancel_order_rejects_non_pending_and_another_users_order(self):
        self.client.force_authenticate(self.user)
        self.client.post(
            reverse("store-cart-add"), {"product_id": self.product.id, "quantity": 1}, format="json"
        )
        order_data = self.client.post(
            reverse("store-checkout"), {"provider": "mercado_pago"}, format="json"
        ).data
        order = Order.objects.get(pk=order_data["id"])
        order.status = "paid"
        order.save(update_fields=["status"])

        paid_response = self.client.post(reverse("store-order-cancel", kwargs={"pk": order.id}))
        other = get_user_model().objects.create_user(
            email="buyer@example.com", username="buyer", password="dojo-test-password"
        )
        self.client.force_authenticate(other)
        other_response = self.client.post(reverse("store-order-cancel", kwargs={"pk": order.id}))

        self.assertEqual(paid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_affiliate_product_redirects_tracks_click_and_never_enters_cart(self):
        partner = CommercePartner.objects.create(
            name="Parceiro Educacional", partner_type="affiliate", website="https://example.com"
        )
        affiliate_product = Product.objects.create(
            category=self.category,
            name="Curso parceiro",
            slug="curso-parceiro",
            product_type="digital",
            sales_model="affiliate",
            price="99.00",
            active=True,
        )
        AffiliateOffer.objects.create(
            product=affiliate_product,
            partner=partner,
            destination_url="https://example.com/curso?ref=3dstore",
        )

        redirect = self.client.get(
            reverse("store-affiliate-redirect", kwargs={"product_id": affiliate_product.id}),
            {"campaign": "catalogo"},
        )
        self.client.force_authenticate(self.user)
        add = self.client.post(
            reverse("store-cart-add"), {"product_id": affiliate_product.id, "quantity": 1}, format="json"
        )

        self.assertEqual(redirect.status_code, status.HTTP_302_FOUND)
        self.assertEqual(redirect.url, "https://example.com/curso?ref=3dstore")
        self.assertTrue(AffiliateClick.objects.filter(offer__product=affiliate_product, campaign="catalogo").exists())
        self.assertEqual(add.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dropship_checkout_creates_supplier_fulfillment(self):
        supplier = CommercePartner.objects.create(name="Fornecedor Nacional", partner_type="supplier")
        dropship_product = Product.objects.create(
            category=self.category,
            name="Webcam parceira",
            slug="webcam-parceira",
            product_type="physical",
            sales_model="dropship",
            price="180.00",
            stock=5,
            active=True,
        )
        DropshipOffer.objects.create(
            product=dropship_product,
            supplier=supplier,
            supplier_sku="WEB-001",
            supplier_cost="110.00",
        )
        self.client.force_authenticate(self.user)
        self.client.post(
            reverse("store-cart-add"), {"product_id": dropship_product.id, "quantity": 2}, format="json"
        )

        response = self.client.post(reverse("store-checkout"), {"provider": "mercado_pago"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        fulfillment = SupplierFulfillment.objects.get(order_item__order_id=response.data["id"])
        self.assertEqual(str(fulfillment.supplier_cost), "220.00")
        self.assertEqual(fulfillment.status, "pending")
