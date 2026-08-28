from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("library", "0005_book_source")]

    operations = [
        migrations.AddField(
            model_name="studioproject",
            name="project_type",
            field=models.CharField(
                choices=[("youtube", "Trilha YouTube"), ("premium", "Formação Premium")],
                default="premium",
                max_length=20,
            ),
        ),
    ]
