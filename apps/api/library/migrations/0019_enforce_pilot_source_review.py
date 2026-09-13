from django.db import migrations


SLUG = "engenharia-ia-arquitetura-sistemas-inteligentes"


def enforce_review(apps, schema_editor):
    Formation = apps.get_model("library", "SenseiFormation")
    Gap = apps.get_model("library", "SenseiUnitSourceGap")
    formation = Formation.objects.get(slug=SLUG)
    unit = formation.modules.get(order=0).study_units.get(order=0)
    unit.curated_sources.filter(title__startswith="Aprendendo Python").update(
        editorial_status="PROPOSED", reviewed_by=None, reviewed_at=None, rejection_reason=""
    )
    Gap.objects.update_or_create(
        unit=unit,
        defaults={
            "status": "OPEN",
            "reason": "NEEDS_SOURCE: nenhuma proposta possui capítulo, seção e páginas confirmados por revisão humana.",
            "requirements": ["Confirmar a edição", "Validar capítulo ou seção", "Registrar páginas ou referência específica"],
            "resolved_by": None,
            "resolved_at": None,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("library", "0018_senseistudyjourney")]
    operations = [migrations.RunPython(enforce_review, migrations.RunPython.noop)]
