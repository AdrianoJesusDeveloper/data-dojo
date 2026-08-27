from django.urls import path
from .views import AffiliateRedirectView, CategoryListView, ProductListView, CartView, CartItemCreateView, CartItemDetailView, CheckoutView, OrderListView, OrderCancelView, ProductQuestionListCreateView, ProductQuestionDetailView, ProductReviewListCreateView, ProductReviewDetailView, SandboxPaymentApproveView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="store-categories"),
    path("products/", ProductListView.as_view(), name="store-products"),
    path("products/<int:product_id>/affiliate/redirect/", AffiliateRedirectView.as_view(), name="store-affiliate-redirect"),
    path("products/<int:product_id>/questions/", ProductQuestionListCreateView.as_view(), name="store-product-questions"),
    path("questions/<int:pk>/", ProductQuestionDetailView.as_view(), name="store-question-detail"),
    path("products/<int:product_id>/reviews/", ProductReviewListCreateView.as_view(), name="store-product-reviews"),
    path("reviews/<int:pk>/", ProductReviewDetailView.as_view(), name="store-review-detail"),
    path("cart/", CartView.as_view(), name="store-cart"),
    path("cart/items/", CartItemCreateView.as_view(), name="store-cart-add"),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="store-cart-item"),
    path("checkout/", CheckoutView.as_view(), name="store-checkout"),
    path("sandbox/orders/<int:pk>/approve/", SandboxPaymentApproveView.as_view(), name="store-sandbox-payment-approve"),
    path("orders/", OrderListView.as_view(), name="store-orders"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="store-order-cancel"),
]
