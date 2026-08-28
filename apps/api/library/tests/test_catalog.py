from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings

from library.models import LibrarySource
from library.services.catalog import resolve_library_file, scan_library


class CatalogTests(TestCase):
    def test_resolver_rejects_traversal_absolute_external_and_missing(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / "library"
            root.mkdir()
            inside = root / "inside.pdf"
            outside = base / "outside.pdf"
            inside.write_bytes(b"inside")
            outside.write_bytes(b"outside")
            self.assertEqual(resolve_library_file(root, Path("inside.pdf")), inside.resolve())
            for candidate in (Path("../outside.pdf"), outside.resolve(), Path("missing.pdf")):
                with self.subTest(candidate=candidate), self.assertRaises((ValueError, FileNotFoundError)):
                    resolve_library_file(root, candidate)

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
