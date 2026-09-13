from django.db import migrations


SLUG = "engenharia-ia-arquitetura-sistemas-inteligentes"
SOURCE_FILENAME = "Aprendendo Python - Mark Lutz e David Ascher.pdf"


def seed_pilot(apps, schema_editor):
    Formation = apps.get_model("library", "SenseiFormation")
    Source = apps.get_model("library", "LibrarySource")
    Plan = apps.get_model("library", "SenseiUnitStudyPlan")
    UnitSource = apps.get_model("library", "SenseiUnitSource")

    formation = Formation.objects.get(slug=SLUG)
    module = formation.modules.get(order=0)
    unit = module.study_units.get(order=0)
    plan, _ = Plan.objects.update_or_create(
        unit=unit,
        defaults={
            "learning_objectives": [
                "Compreender os tipos fundamentais, coleções e seu comportamento em Python.",
                "Explicar com palavras próprias mutabilidade, identidade, igualdade e escolha de estruturas.",
                "Implementar e testar pequenas transformações de dados sem depender da IA para a evidência.",
                "Experimentar entradas inválidas, localizar erros e justificar a solução adotada.",
            ],
            "practices": [
                "Construir exemplos próprios com números, strings, listas, tuplas, conjuntos e dicionários.",
                "Implementar uma transformação de registros usando funções pequenas e tipos explícitos.",
                "Escrever testes para mutabilidade, valores ausentes, entradas inválidas e casos-limite.",
                "Provocar e depurar ao menos dois erros de tipo ou mutabilidade, registrando causa e correção.",
                "Comparar duas estruturas de dados possíveis e justificar a escolha.",
            ],
            "expected_evidence": [
                "Explicação escrita com exemplos próprios.",
                "Código Python executável acompanhado de testes.",
                "Registro dos erros encontrados, diagnóstico e correções.",
                "Resposta oral ou escrita às perguntas de defesa sobre escolhas de tipos e estruturas.",
            ],
            "completion_criteria": [
                "Explica identidade, igualdade e mutabilidade sem copiar a fonte.",
                "Seleciona listas, tuplas, conjuntos e dicionários de acordo com o problema.",
                "Implementa a prática e cobre casos válidos e inválidos com testes.",
                "Depura os erros provocados e justifica as decisões do código.",
                "Produz evidência própria; concluir o estudo não declara competência demonstrada.",
            ],
            "guidance": "Compreender → explicar → implementar → experimentar → errar e depurar → justificar → produzir evidência própria.",
        },
    )
    plan.related_competencies.set(module.competencies.all())
    plan.prerequisites.clear()

    source = Source.objects.filter(filename=SOURCE_FILENAME, status="supported").first()
    if source:
        UnitSource.objects.update_or_create(
            unit=unit, source=source,
            defaults={
                "category": "FOUNDATIONAL",
                "source_type": "TECHNICAL_BOOK",
                "title": "Aprendendo Python — Mark Lutz e David Ascher",
                "reference": "Livro disponível e processado na Biblioteca local do Sensei.",
                "location": "Localizar no sumário as seções sobre tipos fundamentais, coleções, referências e mutabilidade; páginas não informadas sem verificação editorial.",
                "objective": "Fundamentar tipos, coleções, identidade, igualdade e mutabilidade usados na prática da unidade.",
                "priority": 1,
                "notes": "Associação curada pelo título e disponibilidade local. A paginação deve ser preenchida após conferência humana da edição.",
                "is_required": True,
                "url": "",
                "curated_by": None,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("library", "0013_senseistudynote_senseiunitsource_senseiunitstudyplan_and_more")]
    operations = [migrations.RunPython(seed_pilot, migrations.RunPython.noop)]
