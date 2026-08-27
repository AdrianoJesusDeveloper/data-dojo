import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("library", "0003_rename_bookchunk_index"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="StudioProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("theme", models.CharField(max_length=500)),
                ("objective", models.TextField()),
                ("status", models.CharField(choices=[("draft", "Rascunho"), ("planning", "Planejamento"), ("awaiting_approval", "Aguardando aprovação"), ("approved", "Aprovado"), ("implementing", "Em implementação"), ("validating", "Em validação"), ("content", "Produção de conteúdo"), ("complete", "Concluído")], default="draft", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("books", models.ManyToManyField(blank=True, related_name="studio_projects", to="library.book")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="studio_projects", to=settings.AUTH_USER_MODEL)),
                ("source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="projects", to="library.librarysource")),
            ], options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="ModernizationPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_summary", models.TextField(blank=True)), ("original_architecture", models.JSONField(default=dict)),
                ("proposed_architecture", models.JSONField(default=dict)), ("replacements", models.JSONField(default=list)),
                ("requirements", models.JSONField(default=dict)), ("acceptance_criteria", models.JSONField(default=list)),
                ("test_strategy", models.JSONField(default=dict)), ("risks", models.JSONField(default=list)),
                ("business_value", models.TextField(blank=True)), ("raw_response", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Rascunho"), ("review", "Em revisão"), ("approved", "Aprovado")], default="draft", max_length=20)),
                ("version", models.PositiveIntegerField(default=1)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="modernization_plan", to="library.studioproject")),
            ],
        ),
        migrations.CreateModel(
            name="SourceCitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("book_title", models.CharField(blank=True, max_length=255)), ("page_number", models.PositiveIntegerField(blank=True, null=True)),
                ("excerpt", models.TextField()), ("purpose", models.CharField(default="modernization_plan", max_length=120)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("chunk", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="library.bookchunk")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="citations", to="library.studioproject")),
                ("source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="library.librarysource")),
            ],
        ),
        migrations.CreateModel(
            name="StudioApproval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("artifact", models.CharField(default="modernization_plan", max_length=80)),
                ("decision", models.CharField(choices=[("approved", "Aprovado"), ("revision", "Solicitar revisão")], max_length=20)),
                ("notes", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("decided_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approvals", to="library.studioproject")),
            ], options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ContentPackage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("study_plan", models.JSONField(default=dict)), ("lesson", models.JSONField(default=dict)), ("kata", models.JSONField(default=dict)),
                ("video_script", models.JSONField(default=dict)), ("article", models.TextField(blank=True)), ("linkedin_post", models.TextField(blank=True)),
                ("raw_response", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="content_package", to="library.studioproject")),
            ],
        ),
    ]
