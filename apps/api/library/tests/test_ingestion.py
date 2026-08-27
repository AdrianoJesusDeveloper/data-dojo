from django.test import SimpleTestCase

from library.services.ingestion import chunk_text


class ChunkTextTests(SimpleTestCase):
    def test_chunks_keep_page_and_overlap(self):
        result = chunk_text([(3, "um dois tres quatro cinco seis")], chunk_size=4, overlap=2)
        self.assertEqual([chunk["page_number"] for chunk in result], [3, 3])
        self.assertEqual(result[0]["content"], "um dois tres quatro")
        self.assertEqual(result[1]["content"], "tres quatro cinco seis")
        self.assertEqual([chunk["chunk_index"] for chunk in result], [0, 1])

    def test_rejects_invalid_overlap(self):
        with self.assertRaises(ValueError):
            chunk_text([(1, "texto")], chunk_size=10, overlap=10)
