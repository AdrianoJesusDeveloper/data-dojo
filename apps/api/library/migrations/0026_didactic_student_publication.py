import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_courseprogress_completed_at_and_more"),
        ("library", "0025_didacticlesson_source_mode_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="senseiformation", name="workspace_course", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sensei_formation", to="core.course")),
        migrations.AddField(model_name="senseiformationmodule", name="workspace_module", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sensei_module", to="core.module")),
        migrations.AddField(model_name="didacticlesson", name="origin_lesson", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="student_derivation", to="library.didacticlesson")),
        migrations.AddField(model_name="didacticlesson", name="origin_updated_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="didacticlesson", name="workspace_lesson", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="didactic_student_lesson", to="core.lesson")),
        migrations.CreateModel(
            name="DidacticPublication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope", models.CharField(choices=[("LESSON", "Aula"), ("MODULE", "Módulo"), ("FORMATION", "Formação")], max_length=20)),
                ("status", models.CharField(choices=[("PREVIEW", "Prévia"), ("PUBLISHED", "Publicada")], db_index=True, default="PREVIEW", max_length=20)),
                ("preview_token", models.UUIDField(editable=False, unique=True)),
                ("source_snapshot", models.JSONField(default=list)),
                ("preview_payload", models.JSONField(default=list)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="didactic_publications", to=settings.AUTH_USER_MODEL)),
                ("formation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="didactic_publications", to="library.senseiformation")),
                ("module", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="didactic_publications", to="library.senseiformationmodule")),
                ("unit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="didactic_publications", to="library.senseistudyunit")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
