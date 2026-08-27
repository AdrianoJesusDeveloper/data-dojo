from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AffiliateClick, AffiliateOffer, Category, Product, Cart, CartItem, Order, OrderItem, Payment, ProductQuestion, ProductReview, SupplierFulfillment
from .payments import get_payment_gateway
from .payments.base import PaymentConfigurationError
from .serializers import CategorySerializer, ProductSerializer, CartSerializer, CartItemSerializer, OrderSerializer, ProductQuestionSerializer, ProductReviewSerializer


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Product.objects.filter(active=True).select_related(
            "category", "affiliate_offer__partner", "dropship_offer__supplier"
        ).annotate(
            rating_average=Avg("reviews__rating", distinct=True),
            reviews_count=Count("reviews", distinct=True),
            questions_count=Count("questions", distinct=True),
        ).order_by("-featured", "-created_at")
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(short_description__icontains=search)
                | Q(description__icontains=search)
                | Q(category__name__icontains=search)
                | Q(affiliate_offer__partner__name__icontains=search)
                | Q(dropship_offer__supplier__name__icontains=search)
            ).distinct()
        product_type = self.request.query_params.get("product_type")
        if product_type in dict(Product.PRODUCT_TYPES):
            queryset = queryset.filter(product_type=product_type)
        sales_model = self.request.query_params.get("sales_model")
        if sales_model in dict(Product.SALES_MODELS):
            queryset = queryset.filter(sales_model=sales_model)
        return queryset


class AffiliateRedirectView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        offer = generics.get_object_or_404(
            AffiliateOffer.objects.select_related("product", "partner"),
            product_id=product_id,
            product__active=True,
            product__sales_model="affiliate",
            active=True,
            partner__active=True,
        )
        destination_host = offer.destination_url.split("/")[2].split(":")[0]
        if not url_has_allowed_host_and_scheme(
            offer.destination_url, allowed_hosts={destination_host}, require_https=True
        ):
            return Response({"detail": "Link do parceiro inválido."}, status=status.HTTP_400_BAD_REQUEST)
        if not request.session.session_key:
            request.session.create()
        AffiliateClick.objects.create(
            offer=offer,
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key or "",
            campaign=request.query_params.get("campaign", "")[:120],
            referrer=request.headers.get("Referer", "")[:1000],
        )
        return HttpResponseRedirect(offer.destination_url)


class ProductQuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductQuestionSerializer

    def get_permissions(self):
        permission = permissions.IsAuthenticated if self.request.method == "POST" else permissions.AllowAny
        return [permission()]

    def get_product(self):
        return generics.get_object_or_404(Product, pk=self.kwargs["product_id"], active=True)

    def get_queryset(self):
        return ProductQuestion.objects.filter(product=self.get_product()).select_related("user")

    def perform_create(self, serializer):
        serializer.save(product=self.get_product(), user=self.request.user)


class ProductQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ProductQuestion.objects.select_related("user")
        return queryset if self.request.user.is_staff else queryset.filter(user=self.request.user)


class ProductReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductReviewSerializer

    def get_permissions(self):
        permission = permissions.IsAuthenticated if self.request.method == "POST" else permissions.AllowAny
        return [permission()]

    def get_product(self):
        return generics.get_object_or_404(Product, pk=self.kwargs["product_id"], active=True)

    def get_queryset(self):
        return ProductReview.objects.filter(product=self.get_product()).select_related("user", "product")

    def perform_create(self, serializer):
        product = self.get_product()
        if ProductReview.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError({"detail": "Você já avaliou este produto. Edite sua avaliação existente."})
        serializer.save(product=product, user=self.request.user)


class ProductReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ProductReview.objects.select_related("user", "product")
        return queryset if self.request.user.is_staff else queryset.filter(user=self.request.user)


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartItemCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]
        if product.sales_model == "affiliate":
            return Response(
                {"detail": "Produtos afiliados são comprados diretamente no site do parceiro."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if product.sales_model == "dropship" and (
            not hasattr(product, "dropship_offer")
            or not product.dropship_offer.active
            or not product.dropship_offer.supplier.active
        ):
            return Response({"detail": "Fornecedor indisponível no momento."}, status=status.HTTP_400_BAD_REQUEST)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": quantity})
        new_quantity = quantity if created else item.quantity + quantity
        if product.product_type == "physical" and product.stock < new_quantity:
            if created:
                item.delete()
            return Response({"detail": "Estoque insuficiente."}, status=status.HTTP_400_BAD_REQUEST)
        if not created:
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])
        return Response(CartSerializer(cart, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        item = generics.get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        try:
            quantity = int(request.data.get("quantity", 1))
        except (TypeError, ValueError):
            return Response({"detail": "Quantidade inválida."}, status=status.HTTP_400_BAD_REQUEST)
        if quantity < 1:
            return Response({"detail": "Quantidade inválida."}, status=status.HTTP_400_BAD_REQUEST)
        if item.product.product_type == "physical" and item.product.stock < quantity:
            return Response({"detail": "Estoque insuficiente."}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        return Response(CartSerializer(item.cart, context={"request": request}).data)

    def delete(self, request, pk):
        item = generics.get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        cart = item.cart
        item.delete()
        return Response(CartSerializer(cart, context={"request": request}).data)


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        provider = request.data.get("provider", "mercado_pago")
        if provider not in {value for value, _ in Payment.PROVIDERS}:
            return Response({"detail": "Provedor de pagamento inválido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            gateway = get_payment_gateway()
        except PaymentConfigurationError:
            gateway = None
        if gateway is None or not gateway.available:
            return Response(
                {"detail": "O pagamento ainda não está configurado neste ambiente."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            cart = generics.get_object_or_404(Cart.objects.select_for_update(), user=request.user)
            items = list(cart.items.select_related("product"))
            if not items:
                return Response({"detail": "Carrinho vazio."}, status=status.HTTP_400_BAD_REQUEST)

            total = Decimal("0.00")
            locked_products = {}
            for item in items:
                product = Product.objects.select_for_update().get(pk=item.product_id)
                locked_products[item.product_id] = product
                if not product.active:
                    return Response({"detail": f"{product.name} não está disponível."}, status=status.HTTP_400_BAD_REQUEST)
                if product.product_type == "physical" and product.stock < item.quantity:
                    return Response({"detail": f"Estoque insuficiente para {product.name}."}, status=status.HTTP_400_BAD_REQUEST)
                if product.sales_model == "affiliate":
                    return Response({"detail": f"{product.name} deve ser comprado no parceiro."}, status=status.HTTP_400_BAD_REQUEST)
                if product.sales_model == "dropship" and (
                    not hasattr(product, "dropship_offer")
                    or not product.dropship_offer.active
                    or not product.dropship_offer.supplier.active
                ):
                    return Response({"detail": f"Fornecedor de {product.name} indisponível."}, status=status.HTTP_400_BAD_REQUEST)
                total += product.price * item.quantity

            order = Order.objects.create(user=request.user, total=total)
            for item in items:
                product = locked_products[item.product_id]
                order_item = OrderItem.objects.create(order=order, product=product, quantity=item.quantity, unit_price=product.price)
                if product.sales_model == "dropship":
                    SupplierFulfillment.objects.create(
                        order_item=order_item,
                        supplier=product.dropship_offer.supplier,
                        supplier_cost=product.dropship_offer.supplier_cost * item.quantity,
                    )
                if product.product_type == "physical":
                    product.stock -= item.quantity
                    product.save(update_fields=["stock"])

            payment = Payment.objects.create(order=order, amount=total, provider=provider)
            cart.items.all().delete()

        intent = gateway.create_intent(order=order, requested_provider=provider)
        payment.external_id = intent.external_id
        payment.status = intent.status
        payment.raw_response = {**intent.metadata, "checkout_url": intent.checkout_url}
        payment.save(update_fields=["external_id", "status", "raw_response", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)


class SandboxPaymentApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        gateway = get_payment_gateway()
        if not gateway.sandbox:
            return Response({"detail": "Rota indisponível."}, status=status.HTTP_404_NOT_FOUND)
        order = generics.get_object_or_404(
            Order.objects.select_for_update().select_related("payment"),
            pk=pk,
            user=request.user,
            status="pending",
        )
        order.status = "paid"
        order.save(update_fields=["status", "updated_at"])
        order.payment.status = "approved"
        order.payment.raw_response = {**order.payment.raw_response, "sandbox_approved": True}
        order.payment.save(update_fields=["status", "raw_response", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(status="cancelled").select_related("payment").prefetch_related(
            "items__product__category",
            "items__product__reviews",
            "items__product__questions",
        ).order_by("-created_at")


class OrderCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        order = generics.get_object_or_404(
            Order.objects.select_for_update().prefetch_related("items__product"),
            pk=pk,
            user=request.user,
        )
        if order.status != "pending":
            return Response(
                {"detail": "Somente pedidos pendentes podem ser cancelados."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for item in order.items.all():
            if item.product.product_type == "physical":
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.stock += item.quantity
                product.save(update_fields=["stock"])

        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        if hasattr(order, "payment"):
            order.payment.status = "cancelled"
            order.payment.save(update_fields=["status", "updated_at"])

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()

        return Response(OrderSerializer(order, context={"request": request}).data)
