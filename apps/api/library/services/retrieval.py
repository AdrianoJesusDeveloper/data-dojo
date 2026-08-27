import math

from library.models import BookChunk
from .embeddings import generate_embedding


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    return sum(x * y for x, y in zip(left, right)) / denominator if denominator else 0.0


def buscar_chunks_relevantes(query: str, book_ids: list[int], top_k=8) -> list[BookChunk]:
    if not query.strip() or not book_ids or top_k < 1:
        return []
    query_embedding = generate_embedding(query)
    chunks = BookChunk.objects.filter(book_id__in=book_ids, embedding__isnull=False).select_related("book")
    ranked = sorted(chunks, key=lambda chunk: cosine_similarity(query_embedding, chunk.embedding), reverse=True)
    return ranked[:top_k]
