import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Trilha",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120)),
                ("foco", models.TextField(help_text="Descrição do público/foco da trilha")),
                ("ordem", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["ordem", "nome"]},
        ),
        migrations.CreateModel(
            name="Book",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("author", models.CharField(blank=True, max_length=255)),
                ("tecnologias", models.JSONField(blank=True, default=list)),
                ("file", models.FileField(upload_to="library/books/")),
                ("status", models.CharField(choices=[("uploaded", "Enviado"), ("processing", "Processando"), ("ready", "Pronto"), ("error", "Erro")], default="uploaded", max_length=20)),
                ("total_chunks", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("trilha", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="books", to="library.trilha")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BookChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_index", models.PositiveIntegerField()),
                ("page_number", models.PositiveIntegerField(blank=True, null=True)),
                ("content", models.TextField()),
                ("embedding", models.JSONField(blank=True, null=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chunks", to="library.book")),
            ],
            options={"ordering": ["chunk_index"], "indexes": [models.Index(fields=["book", "chunk_index"], name="library_boo_book_id_397ff8_idx")]},
        ),
        migrations.CreateModel(
            name="GeneratedScript",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo_video", models.CharField(max_length=255)),
                ("problema_resolvido", models.TextField()),
                ("ganho_negocio", models.TextField()),
                ("estrutura", models.JSONField(default=dict)),
                ("conteudo_bruto", models.TextField(help_text="Resposta completa gerada pela IA")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("books", models.ManyToManyField(related_name="scripts", to="library.book")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("trilha", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scripts", to="library.trilha")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="bookchunk",
            constraint=models.UniqueConstraint(fields=("book", "chunk_index"), name="unique_book_chunk"),
        ),
    ]
