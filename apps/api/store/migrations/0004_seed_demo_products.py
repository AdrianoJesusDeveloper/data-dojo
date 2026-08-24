from decimal import Decimal

from django.db import migrations


DEMO_PRODUCTS = [
    {
        "category_slug": "ebooks-guias",
        "name": "Python para Dados — Fundamentos Kaizen",
        "slug": "demo-python-dados-fundamentos-kaizen",
        "short_description": "E-book introdutório com exercícios de Python aplicados à análise de dados.",
        "description": "Material fictício de demonstração da 3DStore, com fundamentos, exemplos e desafios progressivos.",
        "product_type": "digital",
        "price": Decimal("39.90"),
        "compare_at_price": Decimal("59.90"),
        "featured": True,
    },
    {
        "category_slug": "ebooks-guias",
        "name": "Guia Prático de SQL para Analytics",
        "slug": "demo-guia-pratico-sql-analytics",
        "short_description": "Consultas, joins, agregações e desafios para construir uma base sólida em SQL.",
        "description": "Guia fictício para demonstração do catálogo e do fluxo de compra da 3DStore.",
        "product_type": "digital",
        "price": Decimal("34.90"),
        "compare_at_price": Decimal("49.90"),
        "featured": True,
    },
    {
        "category_slug": "templates-dados",
        "name": "Kit Portfólio Data Analyst",
        "slug": "demo-kit-portfolio-data-analyst",
        "short_description": "Templates de projetos, documentação e apresentação para seu portfólio.",
        "description": "Pacote digital fictício com modelos de README, estudo de caso e apresentação executiva.",
        "product_type": "digital",
        "price": Decimal("69.90"),
        "compare_at_price": Decimal("89.90"),
        "featured": True,
    },
    {
        "category_slug": "templates-dados",
        "name": "Dataset E-commerce para Projetos",
        "slug": "demo-dataset-ecommerce-projetos",
        "short_description": "Base fictícia para praticar limpeza, exploração, KPIs e visualização de dados.",
        "description": "Dataset demonstrativo com dicionário de dados e sugestões de análises.",
        "product_type": "digital",
        "price": Decimal("24.90"),
        "compare_at_price": None,
        "featured": False,
    },
    {
        "category_slug": "ia-automacao",
        "name": "Biblioteca de Prompts para Dados e IA",
        "slug": "demo-biblioteca-prompts-dados-ia",
        "short_description": "Prompts estruturados para análise, documentação, automação e estudos.",
        "description": "Coleção fictícia organizada por objetivos e níveis de experiência.",
        "product_type": "digital",
        "price": Decimal("29.90"),
        "compare_at_price": Decimal("44.90"),
        "featured": False,
    },
    {
        "category_slug": "ia-automacao",
        "name": "Mentoria Express — Projeto de Dados",
        "slug": "demo-mentoria-express-projeto-dados",
        "short_description": "Sessão fictícia de orientação para estruturar um projeto de portfólio.",
        "description": "Serviço demonstrativo para validar produtos do tipo serviço na 3DStore.",
        "product_type": "service",
        "price": Decimal("149.90"),
        "compare_at_price": None,
        "featured": False,
    },
]


def seed_demo_products(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")

    for item in DEMO_PRODUCTS:
        category = Category.objects.filter(slug=item["category_slug"]).first()
        if category is None:
            continue
        defaults = {key: value for key, value in item.items() if key not in {"category_slug", "slug"}}
        defaults.update({"category": category, "active": True, "stock": 0, "image_url": ""})
        Product.objects.update_or_create(slug=item["slug"], defaults=defaults)


def remove_demo_products(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    Product.objects.filter(slug__in=[item["slug"] for item in DEMO_PRODUCTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("store", "0003_store_v02")]
    operations = [migrations.RunPython(seed_demo_products, remove_demo_products)]
