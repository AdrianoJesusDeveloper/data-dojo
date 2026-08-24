from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("store", "0005_product_questions_reviews"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="sales_model",
            field=models.CharField(
                choices=[("own", "Próprio"), ("affiliate", "Afiliado"), ("dropship", "Dropshipping")],
                default="own",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="CommercePartner",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("partner_type", models.CharField(choices=[("affiliate", "Afiliado"), ("supplier", "Fornecedor"), ("both", "Ambos")], default="affiliate", max_length=20)),
                ("website", models.URLField(blank=True)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("support_url", models.URLField(blank=True)),
                ("terms_url", models.URLField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AffiliateOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("destination_url", models.URLField(max_length=1000)),
                ("commission_type", models.CharField(choices=[("percentage", "Percentual"), ("fixed", "Valor fixo"), ("unknown", "Não informada")], default="unknown", max_length=20)),
                ("commission_value", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("cookie_window_days", models.PositiveIntegerField(blank=True, null=True)),
                ("disclosure", models.CharField(default="Produto de parceiro. A 3DStore poderá receber comissão pela indicação, sem custo adicional para você.", max_length=280)),
                ("active", models.BooleanField(default=True)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("partner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="affiliate_offers", to="store.commercepartner")),
                ("product", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="affiliate_offer", to="store.product")),
            ],
        ),
        migrations.CreateModel(
            name="DropshipOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("supplier_sku", models.CharField(max_length=180)),
                ("supplier_cost", models.DecimalField(decimal_places=2, max_digits=10)),
                ("handling_days", models.PositiveSmallIntegerField(default=2)),
                ("shipping_origin", models.CharField(blank=True, max_length=180)),
                ("supplier_product_url", models.URLField(blank=True, max_length=1000)),
                ("active", models.BooleanField(default=True)),
                ("last_stock_sync_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="dropship_offer", to="store.product")),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="dropship_offers", to="store.commercepartner")),
            ],
        ),
        migrations.CreateModel(
            name="AffiliateClick",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(blank=True, max_length=40)),
                ("campaign", models.CharField(blank=True, max_length=120)),
                ("referrer", models.URLField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("offer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="clicks", to="store.affiliateoffer")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="affiliate_clicks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SupplierFulfillment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("supplier_order_id", models.CharField(blank=True, max_length=180)),
                ("status", models.CharField(choices=[("pending", "Pendente"), ("submitted", "Enviado ao fornecedor"), ("shipped", "Despachado"), ("delivered", "Entregue"), ("cancelled", "Cancelado"), ("exception", "Ocorrência")], default="pending", max_length=20)),
                ("tracking_code", models.CharField(blank=True, max_length=180)),
                ("tracking_url", models.URLField(blank=True, max_length=1000)),
                ("supplier_cost", models.DecimalField(decimal_places=2, max_digits=10)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order_item", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="fulfillment", to="store.orderitem")),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fulfillments", to="store.commercepartner")),
            ],
        ),
    ]
