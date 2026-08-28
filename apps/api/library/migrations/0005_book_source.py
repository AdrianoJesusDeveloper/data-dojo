from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("library", "0004_studio_workflow")]

    operations = [
        migrations.AddField(
            model_name="book",
            name="source",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="book",
                to="library.librarysource",
            ),
        ),
    ]
