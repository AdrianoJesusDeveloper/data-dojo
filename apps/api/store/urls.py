from django.urls import path

from .views import CategoryListView, CartView, CheckoutView, OrderListView, ProductListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="store-categories"),
    path("products/", ProductListView.as_view(), name="store-products"),
    path("cart/", CartView.as_view(), name="store-cart"),
    path("checkout/", CheckoutView.as_view(), name="store-checkout"),
    path("orders/", OrderListView.as_view(), name="store-orders"),
]
