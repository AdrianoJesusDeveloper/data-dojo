import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("professional", "0005_opportunityexecutionartifact"),
        ("library", "0010_senseicompetency_senseicompetencyevidence_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OpportunityExecutionEvidenceLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artifact", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="evidence_links",
                    to="professional.opportunityexecutionartifact",
                )),
                ("evidence", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="professional_execution_links",
                    to="library.senseicompetencyevidence",
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(fields=["artifact", "evidence"], name="unique_exec_artifact_evidence"),
                ],
            },
        ),
    ]
