from django.conf import settings
from django.db import models


class LibrarySource(models.Model):
    STATUS_CHOICES = [
        ("discovered", "Descoberto"),
        ("supported", "Suportado"),
        ("unsupported", "Ainda não suportado"),
        ("missing", "Arquivo ausente"),
    ]

    relative_path = models.TextField(unique=True)
    filename = models.CharField(max_length=500)
    extension = models.CharField(max_length=20)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="discovered")
    modified_at = models.DateTimeField(null=True, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["relative_path"]

    def __str__(self):
        return self.relative_path


class Trilha(models.Model):
    nome = models.CharField(max_length=120)
    foco = models.TextField(help_text="Descrição do público/foco da trilha")
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class Book(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Enviado"),
        ("processing", "Processando"),
        ("ready", "Pronto"),
        ("error", "Erro"),
    ]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    trilha = models.ForeignKey(Trilha, on_delete=models.SET_NULL, null=True, related_name="books")
    tecnologias = models.JSONField(default=list, blank=True)
    file = models.FileField(upload_to="library/books/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")
    total_chunks = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class BookChunk(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    content = models.TextField()
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["book", "chunk_index"], name="unique_book_chunk")]
        indexes = [models.Index(fields=["book", "chunk_index"])]
        ordering = ["chunk_index"]


class GeneratedScript(models.Model):
    trilha = models.ForeignKey(Trilha, on_delete=models.SET_NULL, null=True, related_name="scripts")
    books = models.ManyToManyField(Book, related_name="scripts")
    titulo_video = models.CharField(max_length=255)
    problema_resolvido = models.TextField()
    ganho_negocio = models.TextField()
    estrutura = models.JSONField(default=dict)
    conteudo_bruto = models.TextField(help_text="Resposta completa gerada pela IA")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.titulo_video
