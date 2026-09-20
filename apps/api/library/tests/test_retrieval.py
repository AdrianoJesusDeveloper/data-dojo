from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from library.models import Book, BookChunk
from library.services.retrieval import buscar_chunks_relevantes, cosine_similarity


class CosineSimilarityTests(SimpleTestCase):
    def test_orders_equal_and_opposite_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [-1, 0]), -1.0)

    def test_invalid_dimensions_are_not_similar(self):
        self.assertEqual(cosine_similarity([1], [1, 2]), 0.0)


class RetrievalRangeTests(TestCase):
    @patch("library.services.retrieval.generate_embedding", return_value=[1.0, 0.0])
    def test_retrieval_never_leaves_approved_pdf_ranges(self, _embedding):
        book = Book.objects.create(
            title="Livro de teste",
            file="library/books/teste.pdf",
            status="ready",
        )
        inside = BookChunk.objects.create(
            book=book,
            chunk_index=1,
            page_number=124,
            content="Dentro do intervalo aprovado",
            embedding=[1.0, 0.0],
        )
        BookChunk.objects.create(
            book=book,
            chunk_index=2,
            page_number=212,
            content="Mais semelhante, porém fora do intervalo aprovado",
            embedding=[1.0, 0.0],
        )

        result = buscar_chunks_relevantes(
            "listas mutáveis",
            [book.id],
            top_k=8,
            allowed_ranges_by_book={
                book.id: [{"pdf_start": 122, "pdf_end": 135}],
            },
        )

        self.assertEqual([chunk.id for chunk in result], [inside.id])

    @patch("library.services.retrieval.generate_embedding", return_value=[1.0, 0.0])
    def test_empty_structured_range_returns_no_chunks(self, _embedding):
        book = Book.objects.create(
            title="Livro sem range",
            file="library/books/sem-range.pdf",
            status="ready",
        )
        BookChunk.objects.create(
            book=book,
            chunk_index=1,
            page_number=10,
            content="Não deve escapar",
            embedding=[1.0, 0.0],
        )

        result = buscar_chunks_relevantes(
            "qualquer coisa",
            [book.id],
            allowed_ranges_by_book={book.id: []},
        )

        self.assertEqual(result, [])
