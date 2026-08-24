from decimal import Decimal
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Payment
from .serializers import CategorySerializer, ProductSerializer, CartSerializer, CartItemSerializer, OrderSerializer

class CategoryListView(generics.ListAPIView):
    queryset=Category.objects.filter(active=True); serializer_class=CategorySerializer; permission_classes=[permissions.AllowAny]

class ProductListView(generics.ListAPIView):
    serializer_class=ProductSerializer; permission_classes=[permissions.AllowAny]
    def get_queryset(self):
        qs=Product.objects.filter(active=True).select_related("category"); category=self.request.query_params.get("category"); return qs.filter(category__slug=category) if category else qs

class CartView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def get(self,request):
        cart,_=Cart.objects.get_or_create(user=request.user); return Response(CartSerializer(cart,context={"request":request}).data)

class CartItemCreateView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def post(self,request):
        serializer=CartItemSerializer(data=request.data); serializer.is_valid(raise_exception=True); product=serializer.validated_data["product"]; quantity=serializer.validated_data["quantity"]
        if product.product_type=="physical" and product.stock < quantity: return Response({"detail":"Estoque insuficiente."},status=status.HTTP_400_BAD_REQUEST)
        cart,_=Cart.objects.get_or_create(user=request.user); item,created=CartItem.objects.get_or_create(cart=cart,product=product,defaults={"quantity":quantity})
        if not created: item.quantity += quantity; item.save(update_fields=["quantity"])
        return Response(CartSerializer(cart,context={"request":request}).data,status=status.HTTP_201_CREATED)

class CartItemDetailView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    def patch(self,request,pk):
        item=generics.get_object_or_404(CartItem,pk=pk,cart__user=request.user); quantity=int(request.data.get("quantity",1))
        if quantity<1:return Response({"detail":"Quantidade inválida."},status=400)
        if item.product.product_type=="physical" and item.product.stock<quantity:return Response({"detail":"Estoque insuficiente."},status=400)
        item.quantity=quantity;item.save(update_fields=["quantity"]);return Response(CartSerializer(item.cart).data)
    def delete(self,request,pk):
        item=generics.get_object_or_404(CartItem,pk=pk,cart__user=request.user);item.delete();return Response(status=204)

class CheckoutView(APIView):
    permission_classes=[permissions.IsAuthenticated]
    @transaction.atomic
    def post(self,request):
        cart=generics.get_object_or_404(Cart.objects.select_for_update(),user=request.user); items=list(cart.items.select_related("product"))
        if not items:return Response({"detail":"Carrinho vazio."},status=400)
        total=Decimal("0.00")
        for item in items:
            product=Product.objects.select_for_update().get(pk=item.product_id)
            if not product.active:return Response({"detail":f"{product.name} não está disponível."},status=400)
            if product.product_type=="physical" and product.stock<item.quantity:return Response({"detail":f"Estoque insuficiente para {product.name}."},status=400)
            total += product.price*item.quantity
        order=Order.objects.create(user=request.user,total=total)
        for item in items:
            product=Product.objects.select_for_update().get(pk=item.product_id);OrderItem.objects.create(order=order,product=product,quantity=item.quantity,unit_price=product.price)
            if product.product_type=="physical":product.stock-=item.quantity;product.save(update_fields=["stock"])
        Payment.objects.create(order=order,amount=total,provider=request.data.get("provider","mercado_pago"))
        cart.items.all().delete()
        return Response(OrderSerializer(order).data,status=201)

class OrderListView(generics.ListAPIView):
    serializer_class=OrderSerializer;permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):return Order.objects.filter(user=self.request.user).prefetch_related("items__product").order_by("-created_at")
