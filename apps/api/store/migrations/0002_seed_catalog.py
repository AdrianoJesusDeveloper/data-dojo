from django.db import migrations


def seed_categories(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    for name, slug, description in [
        ("E-books & Guias", "ebooks-guias", "Conhecimento e materiais para a jornada de dados e tecnologia."),
        ("Templates & Dados", "templates-dados", "Templates, datasets e recursos práticos."),
        ("IA & Automação", "ia-automacao", "Recursos para aplicar IA e automação com estratégia."),
    ]:
        Category.objects.get_or_create(slug=slug, defaults={"name": name, "description": description, "active": True})


def reverse_seed(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Category.objects.filter(slug__in=["ebooks-guias", "templates-dados", "ia-automacao"]).delete()


class Migration(migrations.Migration):
    dependencies = [("store", "0001_initial")]
    operations = [migrations.RunPython(seed_categories, reverse_seed)]
