from django.db import migrations


SLUG = "engenharia-ia-arquitetura-sistemas-inteligentes"


def seed_gap(apps, schema_editor):
    Formation = apps.get_model("library", "SenseiFormation")
    Gap = apps.get_model("library", "SenseiUnitSourceGap")
    formation = Formation.objects.get(slug=SLUG)
    unit = formation.modules.get(order=0).study_units.get(order=0)
    unit.curated_sources.update(
        editorial_status="PROPOSED",
        author_or_organization="Mark Lutz e David Ascher",
        justification="O livro local é adequado aos fundamentos de Python, mas capítulo e páginas ainda exigem validação editorial da edição disponível.",
        confidence="0.800",
        reliability_notes="Livro técnico processado na Biblioteca local; referência específica ainda não validada.",
    )
    Gap.objects.update_or_create(
        unit=unit,
        defaults={
            "status": "OPEN",
            "reason": "NEEDS_SOURCE: nenhuma proposta possui capítulo, seção e páginas confirmados por revisão humana.",
            "requirements": ["Confirmar a edição", "Validar capítulo ou seção", "Registrar páginas ou referência específica"],
            "created_by": None,
            "resolved_at": None,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("library", "0015_sensei_source_curator_v1")]
    operations = [migrations.RunPython(seed_gap, migrations.RunPython.noop)]
