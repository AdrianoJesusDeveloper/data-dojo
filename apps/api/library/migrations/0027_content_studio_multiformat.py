import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0026_didactic_student_publication"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="studioproject", name="original_intent", field=models.TextField(blank=True)),
        migrations.AddField(model_name="studioproject", name="research_policy", field=models.CharField(choices=[("ACERVO_ONLY", "Somente acervo"), ("WEB_ONLY", "Somente web"), ("HYBRID", "Acervo e web")], default="ACERVO_ONLY", max_length=20)),
        migrations.CreateModel(name="StudioResearchContext", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("policy", models.CharField(choices=[("ACERVO_ONLY", "Somente acervo"), ("WEB_ONLY", "Somente web"), ("HYBRID", "Acervo e web")], max_length=20)),
            ("query", models.TextField()), ("dossier", models.JSONField(blank=True, default=dict)),
            ("conflicts", models.JSONField(blank=True, default=list)),
            ("status", models.CharField(choices=[("draft", "Rascunho"), ("ready", "Pronto"), ("gap", "Lacuna"), ("failed", "Falhou")], default="draft", max_length=20)),
            ("built_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="research_context", to="library.studioproject")),
        ]),
        migrations.CreateModel(name="StudioResearchEvidence", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("source_kind", models.CharField(choices=[("ACERVO", "Acervo"), ("WEB", "Web"), ("GAP", "Lacuna")], db_index=True, max_length=20)),
            ("url", models.URLField(blank=True, max_length=2000)), ("title", models.CharField(blank=True, max_length=500)),
            ("domain", models.CharField(blank=True, max_length=255)), ("source_type", models.CharField(blank=True, max_length=80)),
            ("query", models.TextField()), ("excerpt", models.TextField(blank=True)), ("retrieved_at", models.DateTimeField()),
            ("metadata", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("chunk", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="studio_research_evidence", to="library.bookchunk")),
            ("context", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="evidence", to="library.studioresearchcontext")),
        ], options={"ordering": ["source_kind", "id"]}),
        migrations.CreateModel(name="StudioArtifact", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("artifact_type", models.CharField(max_length=40)), ("target_type", models.CharField(max_length=20)),
            ("target_id", models.CharField(max_length=255)), ("plan_version", models.PositiveIntegerField()),
            ("generation", models.PositiveIntegerField(default=1)), ("content", models.JSONField(default=dict)),
            ("status", models.CharField(choices=[("DRAFT", "Rascunho"), ("REVIEW", "Em revisão"), ("APPROVED", "Aprovado")], db_index=True, default="DRAFT", max_length=20)),
            ("reviewed_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="studio_artifacts", to=settings.AUTH_USER_MODEL)),
            ("linked_formation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="studio_artifacts", to="library.senseiformation")),
            ("linked_unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="studio_artifacts", to="library.senseistudyunit")),
            ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="artifacts", to="library.studioproject")),
            ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_studio_artifacts", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at", "-id"], "constraints": [models.UniqueConstraint(fields=("project", "target_id", "plan_version", "generation"), name="unique_studio_artifact_generation")]}),
        migrations.CreateModel(name="StudioFormationLink", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("synced_plan_version", models.PositiveIntegerField(default=0)), ("identity_map", models.JSONField(blank=True, default=dict)),
            ("synced_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("formation", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="studio_link", to="library.senseiformation")),
            ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="formation_link", to="library.studioproject")),
        ]),
    ]
