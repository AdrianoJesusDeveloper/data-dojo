from django.test import SimpleTestCase

from library.services.generation import _extract_json


class GenerationParsingTests(SimpleTestCase):
    def test_extracts_structured_json_from_fence(self):
        raw = '''```json
{"titulo_video":"T","problema_resolvido":"P","ganho_negocio":"G","estrutura":{"arquitetura_mental":[]}}
```'''
        self.assertEqual(_extract_json(raw)["titulo_video"], "T")

    def test_rejects_incomplete_payload(self):
        with self.assertRaises(ValueError):
            _extract_json('{"titulo_video":"T"}')
