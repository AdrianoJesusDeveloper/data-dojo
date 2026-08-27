from django.test import SimpleTestCase

from library.services.retrieval import cosine_similarity


class CosineSimilarityTests(SimpleTestCase):
    def test_orders_equal_and_opposite_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [-1, 0]), -1.0)

    def test_invalid_dimensions_are_not_similar(self):
        self.assertEqual(cosine_similarity([1], [1, 2]), 0.0)
