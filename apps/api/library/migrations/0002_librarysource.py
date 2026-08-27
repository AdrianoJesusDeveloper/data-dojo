from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("library", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="LibrarySource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("relative_path", models.TextField(unique=True)),
                ("filename", models.CharField(max_length=500)),
                ("extension", models.CharField(max_length=20)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("sha256", models.CharField(blank=True, db_index=True, max_length=64)),
                ("status", models.CharField(choices=[("discovered", "Descoberto"), ("supported", "Suportado"), ("unsupported", "Ainda não suportado"), ("missing", "Arquivo ausente")], default="discovered", max_length=20)),
                ("modified_at", models.DateTimeField(blank=True, null=True)),
                ("discovered_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["relative_path"]},
        )
    ]
