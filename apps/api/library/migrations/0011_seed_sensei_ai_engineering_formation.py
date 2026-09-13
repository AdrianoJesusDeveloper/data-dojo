from django.db import migrations


SLUG = "engenharia-ia-arquitetura-sistemas-inteligentes"


def create_formation(apps, schema_editor):
    formation = apps.get_model("library", "SenseiFormation")
    formation.objects.get_or_create(
        slug=SLUG,
        defaults={
            "title": "Engenharia de IA Aplicada e Arquitetura de Sistemas Inteligentes",
            "description": "Formação progressiva para desenvolver competência demonstrada em engenharia de IA e sistemas inteligentes.",
            "objective": "Transformar estudo, prática e evidências revisadas em capacidade real de projetar, justificar, depurar e ensinar sistemas inteligentes.",
            "status": "DRAFT",
            "level": "Progressivo",
            "created_by": None,
        },
    )


def remove_formation(apps, schema_editor):
    formation = apps.get_model("library", "SenseiFormation")
    formation.objects.filter(slug=SLUG, created_by__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("library", "0010_senseicompetency_senseicompetencyevidence_and_more")]
    operations = [migrations.RunPython(create_formation, remove_formation)]
