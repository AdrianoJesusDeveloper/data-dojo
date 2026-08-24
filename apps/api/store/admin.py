from django.contrib import admin
from django.utils import timezone

from .models import AffiliateClick, AffiliateOffer, Category, CommercePartner, DropshipOffer, Order, OrderItem, Product, ProductQuestion, ProductReview, SupplierFulfillment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "product_type", "sales_model", "price", "active", "featured")
    list_filter = ("product_type", "sales_model", "active", "featured", "category")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline]


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "created_at", "answered_at")
    list_filter = ("product", "created_at", "answered_at")
    search_fields = ("question", "answer", "user__username", "product__name")
    readonly_fields = ("product", "user", "question", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if "answer" in form.changed_data:
            obj.answered_at = timezone.now() if obj.answer else None
        super().save_model(request, obj, form, change)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "product", "created_at")
    search_fields = ("comment", "user__username", "product__name")


@admin.register(CommercePartner)
class CommercePartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "partner_type", "active", "contact_email")
    list_filter = ("partner_type", "active")
    search_fields = ("name", "contact_email")


@admin.register(AffiliateOffer)
class AffiliateOfferAdmin(admin.ModelAdmin):
    list_display = ("product", "partner", "commission_type", "commission_value", "active", "last_checked_at")
    list_filter = ("active", "partner", "commission_type")
    search_fields = ("product__name", "partner__name", "destination_url")


@admin.register(DropshipOffer)
class DropshipOfferAdmin(admin.ModelAdmin):
    list_display = ("product", "supplier", "supplier_sku", "supplier_cost", "handling_days", "active")
    list_filter = ("active", "supplier")
    search_fields = ("product__name", "supplier__name", "supplier_sku")


@admin.register(AffiliateClick)
class AffiliateClickAdmin(admin.ModelAdmin):
    list_display = ("offer", "user", "campaign", "created_at")
    list_filter = ("offer__partner", "created_at")
    search_fields = ("offer__product__name", "campaign", "user__username")
    readonly_fields = ("offer", "user", "session_key", "campaign", "referrer", "created_at")


@admin.register(SupplierFulfillment)
class SupplierFulfillmentAdmin(admin.ModelAdmin):
    list_display = ("order_item", "supplier", "status", "tracking_code", "updated_at")
    list_filter = ("status", "supplier")
    search_fields = ("supplier_order_id", "tracking_code")
