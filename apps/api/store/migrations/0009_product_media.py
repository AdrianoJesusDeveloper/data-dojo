import django.core.validators
import store.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("store", "0008_store_query_indexes")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Upload opcional (JPG, PNG ou WebP; máximo 5 MB). Tem prioridade sobre a URL da imagem.",
                upload_to="store/products/%Y/%m/",
                validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
                    store.models.validate_product_image_size,
                ],
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="video_url",
            field=models.URLField(
                blank=True,
                help_text="URL pública do YouTube, Vimeo ou de um arquivo MP4/WebM.",
                max_length=1000,
            ),
        ),
    ]
