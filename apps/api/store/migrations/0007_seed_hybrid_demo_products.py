from decimal import Decimal

from django.db import migrations


def seed_hybrid_products(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    CommercePartner = apps.get_model("store", "CommercePartner")
    AffiliateOffer = apps.get_model("store", "AffiliateOffer")
    DropshipOffer = apps.get_model("store", "DropshipOffer")

    category = Category.objects.filter(slug="ia-automacao").first()
    if category is None:
        return

    affiliate_partner, _ = CommercePartner.objects.get_or_create(
        name="Parceiro Educacional — Demonstração",
        defaults={"partner_type": "affiliate", "website": "https://example.com", "active": True},
    )
    affiliate_product, _ = Product.objects.update_or_create(
        slug="demo-curso-marketing-dados-parceiro",
        defaults={
            "category": category,
            "name": "Curso de Marketing Orientado a Dados — Demo",
            "short_description": "Oferta fictícia para demonstrar o fluxo transparente de produtos afiliados.",
            "description": "Produto demonstrativo. Substitua o parceiro e o link antes de uma divulgação comercial.",
            "product_type": "digital",
            "sales_model": "affiliate",
            "price": Decimal("89.90"),
            "stock": 0,
            "active": True,
            "featured": False,
        },
    )
    AffiliateOffer.objects.update_or_create(
        product=affiliate_product,
        defaults={
            "partner": affiliate_partner,
            "destination_url": "https://example.com/",
            "commission_type": "unknown",
            "active": True,
        },
    )

    supplier, _ = CommercePartner.objects.get_or_create(
        name="Fornecedor Tech Nacional — Demonstração",
        defaults={"partner_type": "supplier", "website": "https://example.com", "active": True},
    )
    dropship_product, _ = Product.objects.update_or_create(
        slug="demo-kit-home-office-criador",
        defaults={
            "category": category,
            "name": "Kit Home Office para Criadores — Demo",
            "short_description": "Kit físico fictício para validar estoque, pedido e acompanhamento do fornecedor.",
            "description": "Produto demonstrativo de dropshipping nacional.",
            "product_type": "physical",
            "sales_model": "dropship",
            "price": Decimal("249.90"),
            "stock": 12,
            "active": True,
            "featured": False,
        },
    )
    DropshipOffer.objects.update_or_create(
        product=dropship_product,
        defaults={
            "supplier": supplier,
            "supplier_sku": "DEMO-KIT-HO-001",
            "supplier_cost": Decimal("149.90"),
            "handling_days": 2,
            "shipping_origin": "São Paulo/SP",
            "supplier_product_url": "https://example.com/",
            "active": True,
        },
    )


def remove_hybrid_products(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    CommercePartner = apps.get_model("store", "CommercePartner")
    Product.objects.filter(slug__in=["demo-curso-marketing-dados-parceiro", "demo-kit-home-office-criador"]).delete()
    CommercePartner.objects.filter(name__endswith="— Demonstração").delete()


class Migration(migrations.Migration):
    dependencies = [("store", "0006_hybrid_commerce")]
    operations = [migrations.RunPython(seed_hybrid_products, remove_hybrid_products)]
