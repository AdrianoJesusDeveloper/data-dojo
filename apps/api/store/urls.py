from django.urls import path
from .views import CategoryListView, ProductListView, CartView, CartItemCreateView, CartItemDetailView, CheckoutView, OrderListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="store-categories"),
    path("products/", ProductListView.as_view(), name="store-products"),
    path("cart/", CartView.as_view(), name="store-cart"),
    path("cart/items/", CartItemCreateView.as_view(), name="store-cart-add"),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="store-cart-item"),
    path("checkout/", CheckoutView.as_view(), name="store-checkout"),
    path("orders/", OrderListView.as_view(), name="store-orders"),
]
