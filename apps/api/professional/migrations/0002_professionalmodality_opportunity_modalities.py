from django.db import migrations, models


CATALOG = [
    ("Desenvolvimento de Software", "software-development", "SOFTWARE_DEVELOPMENT"),
    ("Desenvolvimento Web", "web-development", "SOFTWARE_DEVELOPMENT"),
    ("Frontend", "frontend", "SOFTWARE_DEVELOPMENT"),
    ("Backend", "backend", "SOFTWARE_DEVELOPMENT"),
    ("APIs / Integrações", "apis-integrations", "SOFTWARE_DEVELOPMENT"),
    ("Dados", "data", "DATA"), ("BI", "bi", "DATA"),
    ("Analytics", "analytics", "DATA"),
    ("Engenharia de Dados", "data-engineering", "DATA"),
    ("Ciência de Dados", "data-science", "DATA"),
    ("Inteligência Artificial", "artificial-intelligence", "AI_AUTOMATION"),
    ("Agentes de IA", "ai-agents", "AI_AUTOMATION"),
    ("Automação", "automation", "AI_AUTOMATION"),
    ("Cloud", "cloud", "CLOUD_INFRA"), ("DevOps", "devops", "CLOUD_INFRA"),
    ("Marketing Digital", "digital-marketing", "MARKETING"),
    ("Tráfego Pago", "paid-traffic", "MARKETING"), ("SEO", "seo", "MARKETING"),
    ("Conteúdo / Social Media", "content-social-media", "MARKETING"),
    ("CRM", "crm", "BUSINESS_SYSTEMS"), ("E-commerce", "e-commerce", "BUSINESS_SYSTEMS"),
    ("Consultoria", "consulting", "OTHER"),
    ("Treinamento / Educação", "training-education", "OTHER"), ("Outro", "other", "OTHER"),
]


def seed_modalities(apps, schema_editor):
    modality_model = apps.get_model("professional", "ProfessionalModality")
    for sort_order, (name, slug, domain) in enumerate(CATALOG, start=1):
        modality_model.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "domain": domain, "is_active": True, "sort_order": sort_order},
        )


def remove_seeded_modalities(apps, schema_editor):
    modality_model = apps.get_model("professional", "ProfessionalModality")
    modality_model.objects.filter(slug__in=[item[1] for item in CATALOG]).delete()


class Migration(migrations.Migration):
    dependencies = [("professional", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="ProfessionalModality",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("domain", models.CharField(choices=[("SOFTWARE_DEVELOPMENT", "Desenvolvimento de Software"), ("DATA", "Dados"), ("AI_AUTOMATION", "IA / Automação"), ("CLOUD_INFRA", "Cloud / Infra"), ("MARKETING", "Marketing"), ("BUSINESS_SYSTEMS", "Negócios / Sistemas"), ("OTHER", "Outros")], max_length=30)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.AddField(
            model_name="opportunity",
            name="modalities",
            field=models.ManyToManyField(blank=True, related_name="opportunities", to="professional.professionalmodality"),
        ),
        migrations.RunPython(seed_modalities, remove_seeded_modalities),
    ]
