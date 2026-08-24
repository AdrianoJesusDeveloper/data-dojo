from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0005_studentproject")]

    operations = [
        migrations.AddField(model_name="user", name="github_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="user", name="linkedin_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="user", name="instagram_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="user", name="website_url", field=models.URLField(blank=True)),
    ]
