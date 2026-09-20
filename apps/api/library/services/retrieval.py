import math

from django.db.models import Q

from library.models import BookChunk
from .embeddings import generate_embedding


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    return sum(x * y for x, y in zip(left, right)) / denominator if denominator else 0.0


def buscar_chunks_relevantes(
    query: str,
    book_ids: list[int],
    top_k=8,
    allowed_ranges_by_book: dict[int, list[dict]] | None = None,
) -> list[BookChunk]:
    if not query.strip() or not book_ids or top_k < 1:
        return []

    query_embedding = generate_embedding(query)
    chunks = BookChunk.objects.filter(
        book_id__in=book_ids,
        embedding__isnull=False,
        book__lifecycle="active",
        book__duplicate_of__isnull=True,
    )

    if allowed_ranges_by_book is not None:
        range_filter = Q()
        for book_id in book_ids:
            ranges = allowed_ranges_by_book.get(book_id, [])
            for item in ranges:
                start = int(item.get("pdf_start") or 0)
                end = int(item.get("pdf_end") or 0)
                if start > 0 and end >= start:
                    range_filter |= Q(
                        book_id=book_id,
                        page_number__gte=start,
                        page_number__lte=end,
                    )
        if not range_filter.children:
            return []
        chunks = chunks.filter(range_filter)

    chunks = chunks.select_related("book")
    ranked = sorted(
        chunks,
        key=lambda chunk: cosine_similarity(query_embedding, chunk.embedding),
        reverse=True,
    )
    return ranked[:top_k]
