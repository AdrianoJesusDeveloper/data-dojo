from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("store", "0002_seed_catalog"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="product", name="stock", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="order", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AlterField(model_name="order", name="status", field=models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("processing", "Processing"), ("fulfilled", "Fulfilled"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
        migrations.CreateModel(name="Cart", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("updated_at", models.DateTimeField(auto_now=True)), ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="store_cart", to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name="CartItem", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("quantity", models.PositiveIntegerField(default=1)), ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="store.cart")), ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="store.product"))], options={"constraints": [models.UniqueConstraint(fields=("cart", "product"), name="unique_cart_product")]}),
        migrations.CreateModel(name="Payment", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("provider", models.CharField(choices=[("mercado_pago", "Mercado Pago"), ("stripe", "Stripe")], default="mercado_pago", max_length=30)), ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled"), ("refunded", "Refunded")], default="pending", max_length=20)), ("external_id", models.CharField(blank=True, max_length=180)), ("payment_method", models.CharField(blank=True, max_length=50)), ("amount", models.DecimalField(decimal_places=2, max_digits=10)), ("raw_response", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payment", to="store.order"))]),
    ]
