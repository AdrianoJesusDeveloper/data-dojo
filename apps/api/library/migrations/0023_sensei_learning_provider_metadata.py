from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0022_seed_sensei_marketing_formation"),
    ]

    operations = [
        migrations.AddField(
            model_name="senseilearningactivity",
            name="ai_model",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="senseilearningactivity",
            name="ai_provider",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="senseilearningattempt",
            name="ai_model",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="senseilearningattempt",
            name="ai_provider",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.CreateModel(
            name="SenseiLearningProviderPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("formation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_provider_preferences", to="library.senseiformation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sensei_learning_provider_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("user", "formation"), name="unique_sensei_provider_preference")],
            },
        ),
    ]
