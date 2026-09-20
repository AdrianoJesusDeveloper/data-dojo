import re

from django.db import migrations, models


PDF_RANGE_RE = re.compile(
    r"PDF\s*p\.?\s*(\d+)\s*(?:a|até|-|–|—)\s*(\d+)",
    re.IGNORECASE,
)
PDF_SINGLE_RE = re.compile(r"PDF\s*p\.?\s*(\d+)", re.IGNORECASE)


def backfill_approved_ranges(apps, schema_editor):
    SenseiUnitSource = apps.get_model("library", "SenseiUnitSource")

    for source in SenseiUnitSource.objects.exclude(location="").iterator():
        location = source.location or ""
        ranges = []
        consumed = []

        for match in PDF_RANGE_RE.finditer(location):
            start = int(match.group(1))
            end = int(match.group(2))
            if end < start:
                start, end = end, start
            ranges.append({"pdf_start": start, "pdf_end": end})
            consumed.append(match.span())

        for match in PDF_SINGLE_RE.finditer(location):
            if any(left <= match.start() < right for left, right in consumed):
                continue
            page = int(match.group(1))
            ranges.append({"pdf_start": page, "pdf_end": page})

        unique = []
        seen = set()
        for item in ranges:
            key = (item["pdf_start"], item["pdf_end"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        if unique:
            source.approved_ranges = unique
            source.save(update_fields=["approved_ranges"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0033_booktocentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="senseiunitsource",
            name="approved_ranges",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Intervalos estruturados aprovados para grounding, usando páginas físicas do PDF.",
            ),
        ),
        migrations.AddField(
            model_name="didacticlesson",
            name="grounding_snapshot",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Snapshot imutável das fontes e chunks realmente enviados à IA na geração.",
            ),
        ),
        migrations.RunPython(backfill_approved_ranges, noop),
    ]
