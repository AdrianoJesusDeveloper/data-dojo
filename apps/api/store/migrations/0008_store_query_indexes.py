from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("store", "0007_seed_hybrid_demo_products")]

    operations = [
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["active", "sales_model", "-created_at"],
                name="store_product_catalog_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["active", "category", "product_type"],
                name="store_product_filter_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["user", "-created_at"],
                name="store_order_user_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["status", "-created_at"],
                name="store_order_status_date_idx",
            ),
        ),
    ]
