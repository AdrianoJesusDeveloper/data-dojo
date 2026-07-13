from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_user_options_alter_user_managers_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Exercise",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("statement", models.TextField(blank=True)),
                ("answer_type", models.CharField(choices=[("SQL", "SQL"), ("PYTHON", "Python"), ("MULTIPLE_CHOICE", "Múltipla escolha"), ("OPEN", "Resposta aberta")], default="SQL", max_length=30)),
                ("expected_answer", models.TextField(blank=True)),
                ("expected_keywords", models.JSONField(blank=True, default=list)),
                ("evaluation_mode", models.CharField(choices=[("keywords", "Palavras-chave"), ("exact", "Texto exato"), ("contains", "Contém resposta esperada")], default="keywords", max_length=20)),
                ("points", models.PositiveIntegerField(default=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("lesson", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="exercise", to="core.lesson")),
            ],
        ),
    ]
