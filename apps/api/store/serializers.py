from rest_framework import serializers
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Payment, ProductQuestion, ProductReview


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    rating_average = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    affiliate_disclosure = serializers.SerializerMethodField()
    fulfillment_details = serializers.SerializerMethodField()

    def get_rating_average(self, obj):
        value = getattr(obj, "rating_average", None)
        return round(float(value), 1) if value is not None else None

    def get_reviews_count(self, obj):
        return getattr(obj, "reviews_count", obj.reviews.count())

    def get_questions_count(self, obj):
        return getattr(obj, "questions_count", obj.questions.count())

    def get_partner_name(self, obj):
        if obj.sales_model == "affiliate" and hasattr(obj, "affiliate_offer"):
            return obj.affiliate_offer.partner.name
        if obj.sales_model == "dropship" and hasattr(obj, "dropship_offer"):
            return obj.dropship_offer.supplier.name
        return None

    def get_affiliate_disclosure(self, obj):
        if obj.sales_model == "affiliate" and hasattr(obj, "affiliate_offer") and obj.affiliate_offer.active:
            return obj.affiliate_offer.disclosure
        return None

    def get_fulfillment_details(self, obj):
        if obj.sales_model != "dropship" or not hasattr(obj, "dropship_offer"):
            return None
        offer = obj.dropship_offer
        return {"handling_days": offer.handling_days, "shipping_origin": offer.shipping_origin}

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "short_description", "description", "product_type", "sales_model", "price", "compare_at_price", "image_url", "stock", "featured", "category", "rating_average", "reviews_count", "questions_count", "partner_name", "affiliate_disclosure", "fulfillment_details"]


class ProductQuestionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ProductQuestion
        fields = ["id", "product", "username", "question", "answer", "answered_at", "created_at", "updated_at", "is_owner"]
        read_only_fields = ["product", "answer", "answered_at"]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user == obj.user)


class ProductReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    is_owner = serializers.SerializerMethodField()
    verified_purchase = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = ["id", "product", "username", "rating", "comment", "verified_purchase", "created_at", "updated_at", "is_owner"]
        read_only_fields = ["product"]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("A nota deve estar entre 1 e 5.")
        return value

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user == obj.user)

    def get_verified_purchase(self, obj):
        return OrderItem.objects.filter(
            product=obj.product,
            order__user=obj.user,
            order__status__in=["paid", "processing", "fulfilled"],
        ).exists()


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(source="product", queryset=Product.objects.filter(active=True), write_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_id", "quantity", "subtotal"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantidade deve ser maior que zero.")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total", "updated_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "unit_price", "subtotal"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "provider", "status", "external_id", "payment_method", "amount", "created_at", "updated_at"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "total", "items", "payment", "created_at", "updated_at"]
