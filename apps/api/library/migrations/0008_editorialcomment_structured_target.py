from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("library", "0007_editorial_workflow")]

    operations = [
        migrations.AddField(model_name="editorialcomment", name="plan_version", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="editorialcomment", name="target_id", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(
            model_name="editorialcomment", name="target_type",
            field=models.CharField(choices=[("plan", "Plan"), ("module", "Module"), ("lesson", "Lesson"), ("video", "Video"), ("project", "Project"), ("section", "Section")], default="plan", max_length=20),
        ),
    ]
