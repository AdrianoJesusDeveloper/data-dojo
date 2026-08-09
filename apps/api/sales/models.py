from django.db import models
from core.models import User


class Product(models.Model):

    class ProductType(models.TextChoices):
        COURSE = "course", "Curso"
        MENTORSHIP = "mentorship", "Mentoria"
        EBOOK = "ebook", "E-book"
        SUBSCRIPTION = "subscription", "Assinatura"

    name = models.CharField(max_length=200)

    slug = models.SlugField(unique=True)

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class Order(models.Model):

    class Status(models.TextChoices):

        PENDING = "pending"

        PAID = "paid"

        CANCELLED = "cancelled"

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
class Payment(models.Model):

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE
    )

    transaction_id = models.CharField(max_length=255)

    provider = models.CharField(max_length=50)

    status = models.CharField(max_length=30)

    qr_code = models.TextField()

    pix_code = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)