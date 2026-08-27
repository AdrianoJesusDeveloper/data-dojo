from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _get_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Instale sentence-transformers para gerar embeddings.") from exc
    return SentenceTransformer(settings.LIBRARY_EMBEDDING_MODEL)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [vector.tolist() for vector in vectors]


def generate_embedding(text: str) -> list[float]:
    return generate_embeddings([text])[0]
