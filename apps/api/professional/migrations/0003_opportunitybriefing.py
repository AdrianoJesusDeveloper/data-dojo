from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("professional", "0002_professionalmodality_opportunity_modalities"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="OpportunityBriefing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("raw_source_text", models.TextField()), ("problem", models.TextField(blank=True)),
                ("objective", models.TextField(blank=True)), ("target_audience", models.TextField(blank=True)),
                ("deliverables", models.JSONField(default=list)), ("functional_requirements", models.JSONField(default=list)),
                ("non_functional_requirements", models.JSONField(default=list)), ("integrations", models.JSONField(default=list)),
                ("data_requirements", models.JSONField(default=list)), ("infrastructure_requirements", models.JSONField(default=list)),
                ("constraints", models.JSONField(default=list)), ("dependencies", models.JSONField(default=list)),
                ("assumptions", models.JSONField(default=list)), ("scope_risks", models.JSONField(default=list)),
                ("ambiguities", models.JSONField(default=list)), ("client_questions", models.JSONField(default=list)),
                ("acceptance_criteria", models.JSONField(default=list)), ("ai_provider", models.CharField(max_length=80)),
                ("ai_model", models.CharField(blank=True, max_length=120)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="professional_briefings", to=settings.AUTH_USER_MODEL)),
                ("opportunity", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="intelligent_briefing", to="professional.opportunity")),
            ],
        ),
    ]
