from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def validate_product_image_size(image):
    if image.size > 5 * 1024 * 1024:
        raise ValidationError("A imagem deve ter no máximo 5 MB.")


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class CommercePartner(models.Model):
    PARTNER_TYPES = [("affiliate", "Afiliado"), ("supplier", "Fornecedor"), ("both", "Ambos")]
    name = models.CharField(max_length=180)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPES, default="affiliate")
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    support_url = models.URLField(blank=True)
    terms_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    PRODUCT_TYPES = [("digital", "Digital"), ("physical", "Physical"), ("service", "Service")]
    SALES_MODELS = [("own", "Próprio"), ("affiliate", "Afiliado"), ("dropship", "Dropshipping")]
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    short_description = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default="digital")
    sales_model = models.CharField(max_length=20, choices=SALES_MODELS, default="own")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(blank=True)
    image = models.ImageField(
        upload_to="store/products/%Y/%m/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_product_image_size,
        ],
        help_text="Upload opcional (JPG, PNG ou WebP; máximo 5 MB). Tem prioridade sobre a URL da imagem.",
    )
    video_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text="URL pública do YouTube, Vimeo ou de um arquivo MP4/WebM.",
    )
    digital_url = models.URLField(blank=True)
    stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-featured", "-created_at"]
        indexes = [
            models.Index(fields=["active", "sales_model", "-created_at"], name="store_product_catalog_idx"),
            models.Index(fields=["active", "category", "product_type"], name="store_product_filter_idx"),
        ]

    def __str__(self):
        return self.name


class AffiliateOffer(models.Model):
    COMMISSION_TYPES = [("percentage", "Percentual"), ("fixed", "Valor fixo"), ("unknown", "Não informada")]
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="affiliate_offer")
    partner = models.ForeignKey(CommercePartner, on_delete=models.PROTECT, related_name="affiliate_offers")
    destination_url = models.URLField(max_length=1000)
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPES, default="unknown")
    commission_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cookie_window_days = models.PositiveIntegerField(null=True, blank=True)
    disclosure = models.CharField(max_length=280, default="Produto de parceiro. A 3DStore poderá receber comissão pela indicação, sem custo adicional para você.")
    active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} — {self.partner.name}"


class DropshipOffer(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="dropship_offer")
    supplier = models.ForeignKey(CommercePartner, on_delete=models.PROTECT, related_name="dropship_offers")
    supplier_sku = models.CharField(max_length=180)
    supplier_cost = models.DecimalField(max_digits=10, decimal_places=2)
    handling_days = models.PositiveSmallIntegerField(default=2)
    shipping_origin = models.CharField(max_length=180, blank=True)
    supplier_product_url = models.URLField(max_length=1000, blank=True)
    active = models.BooleanField(default=True)
    last_stock_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} — {self.supplier.name}"


class AffiliateClick(models.Model):
    offer = models.ForeignKey(AffiliateOffer, on_delete=models.CASCADE, related_name="clicks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="affiliate_clicks")
    session_key = models.CharField(max_length=40, blank=True)
    campaign = models.CharField(max_length=120, blank=True)
    referrer = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SupplierFulfillment(models.Model):
    STATUS_CHOICES = [("pending", "Pendente"), ("submitted", "Enviado ao fornecedor"), ("shipped", "Despachado"), ("delivered", "Entregue"), ("cancelled", "Cancelado"), ("exception", "Ocorrência")]
    order_item = models.OneToOneField("OrderItem", on_delete=models.CASCADE, related_name="fulfillment")
    supplier = models.ForeignKey(CommercePartner, on_delete=models.PROTECT, related_name="fulfillments")
    supplier_order_id = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    tracking_code = models.CharField(max_length=180, blank=True)
    tracking_url = models.URLField(max_length=1000, blank=True)
    supplier_cost = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProductQuestion(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="questions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_questions")
    question = models.TextField(max_length=1000)
    answer = models.TextField(max_length=2000, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pergunta sobre {self.product.name} por {self.user.username}"


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["product", "user"], name="unique_product_review_user"),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_1_to_5"),
        ]

    def __str__(self):
        return f"{self.rating}/5 para {self.product.name}"


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store_cart")
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.select_related("product").all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "product"], name="unique_cart_product")]

    @property
    def subtotal(self):
        return self.quantity * self.product.price


class Order(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("paid", "Paid"), ("processing", "Processing"), ("cancelled", "Cancelled"), ("fulfilled", "Fulfilled")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="store_orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"], name="store_order_user_date_idx"),
            models.Index(fields=["status", "-created_at"], name="store_order_status_date_idx"),
        ]

    def __str__(self):
        return f"Pedido #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Payment(models.Model):
    PROVIDERS = [("mercado_pago", "Mercado Pago"), ("stripe", "Stripe")]
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled"), ("refunded", "Refunded")]
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=30, choices=PROVIDERS, default="mercado_pago")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    external_id = models.CharField(max_length=180, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
