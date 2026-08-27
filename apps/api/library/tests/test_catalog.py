from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from library.models import LibrarySource
from library.services.catalog import scan_library


class CatalogTests(TestCase):
    def test_catalogs_supported_files_and_detects_duplicates(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "livro-a.pdf").write_bytes(b"same")
            (root / "livro-b.pdf").write_bytes(b"same")
            (root / "notas.epub").write_bytes(b"epub")
            (root / "ignorar.exe").write_bytes(b"no")
            with override_settings(LOCAL_LIBRARY_PATH=root):
                result = scan_library()

        self.assertEqual(result["total"], 3)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(LibrarySource.objects.filter(status="supported").count(), 2)
        self.assertEqual(LibrarySource.objects.filter(status="unsupported").count(), 1)
