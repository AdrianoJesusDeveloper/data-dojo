from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0004_community_interactions"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("summary", models.CharField(max_length=320)),
                ("description", models.TextField(blank=True)),
                ("technologies", models.JSONField(blank=True, default=list)),
                ("repository_url", models.URLField(blank=True)),
                ("demo_url", models.URLField(blank=True)),
                ("image_url", models.URLField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Rascunho"), ("published", "Publicado")], default="draft", max_length=20)),
                ("featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_projects", to="core.course")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portfolio_projects", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-featured", "-updated_at"]},
        ),
    ]
