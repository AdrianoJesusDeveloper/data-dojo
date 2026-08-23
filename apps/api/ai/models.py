from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    # Null para permitir conversas públicas do AI Sales.
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
    )

    mentor = models.CharField(max_length=50)

    title = models.CharField(
        max_length=200,
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner = self.user.username if self.user else "visitante"
        return f"{owner} - {self.mentor}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(max_length=20)

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}"