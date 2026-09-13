import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import SimpleTestCase

from unittest.mock import patch

from library.services.ingestion import (
    chunk_text,
    extract_document,
    extract_text_by_page,
    extract_text_from_epub,
)


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

class ExtractTextByPageTests(SimpleTestCase):
    @patch("library.services.ingestion._extract_with_ocr")
    @patch("library.services.ingestion._extract_with_pypdf")
    @patch("pypdf.PdfReader")
    def test_does_not_use_ocr_when_all_pages_have_text(
        self, mock_reader, mock_pypdf, mock_ocr
    ):
        mock_reader.return_value.pages = [object(), object()]
        mock_pypdf.return_value = [(1, "pagina um"), (2, "pagina dois")]

        result = extract_text_by_page("livro.pdf")

        self.assertEqual(result, [(1, "pagina um"), (2, "pagina dois")])
        mock_ocr.assert_not_called()

    @patch("library.services.ingestion._extract_with_ocr")
    @patch("library.services.ingestion._extract_with_pypdf")
    @patch("pypdf.PdfReader")
    def test_uses_ocr_as_fallback_when_pdf_has_no_text(
        self, mock_reader, mock_pypdf, mock_ocr
    ):
        mock_reader.return_value.pages = [object()]
        mock_pypdf.return_value = []
        mock_ocr.return_value = [(1, "texto reconhecido por ocr")]

        result = extract_text_by_page("escaneado.pdf")

        self.assertEqual(result, [(1, "texto reconhecido por ocr")])
        mock_ocr.assert_called_once_with("escaneado.pdf")

    @patch("library.services.ingestion._extract_with_ocr")
    @patch("library.services.ingestion._extract_with_pypdf")
    @patch("pypdf.PdfReader")
    def test_combines_text_and_ocr_for_mixed_pdf(
        self, mock_reader, mock_pypdf, mock_ocr
    ):
        mock_reader.return_value.pages = [object(), object(), object()]
        mock_pypdf.return_value = [(1, "texto digital"), (3, "outro texto digital")]
        mock_ocr.return_value = [
            (1, "ocr que nao deve substituir"),
            (2, "texto escaneado"),
            (3, "ocr que nao deve substituir"),
        ]

        result = extract_text_by_page("misto.pdf")

        self.assertEqual(
            result,
            [
                (1, "texto digital"),
                (2, "texto escaneado"),
                (3, "outro texto digital"),
            ],
        )
        mock_ocr.assert_called_once_with("misto.pdf")
        
class ExtractEpubTests(SimpleTestCase):
    def _create_epub(self, path: Path):
        container_xml = """<?xml version="1.0"?>
        <container version="1.0"
          xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <rootfiles>
            <rootfile full-path="OEBPS/content.opf"
              media-type="application/oebps-package+xml"/>
          </rootfiles>
        </container>
        """

        content_opf = """<?xml version="1.0" encoding="UTF-8"?>
        <package version="3.0"
          xmlns="http://www.idpf.org/2007/opf">
          <manifest>
            <item id="cap1"
              href="capitulo1.xhtml"
              media-type="application/xhtml+xml"/>
            <item id="cap2"
              href="capitulo2.xhtml"
              media-type="application/xhtml+xml"/>
          </manifest>
          <spine>
            <itemref idref="cap1"/>
            <itemref idref="cap2"/>
          </spine>
        </package>
        """

        capitulo1 = """
        <html xmlns="http://www.w3.org/1999/xhtml">
          <body>
            <h1>Capítulo 1</h1>
            <p>Primeiro conteúdo do livro.</p>
          </body>
        </html>
        """

        capitulo2 = """
        <html xmlns="http://www.w3.org/1999/xhtml">
          <body>
            <h1>Capítulo 2</h1>
            <p>Segundo conteúdo do livro.</p>
          </body>
        </html>
        """

        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("META-INF/container.xml", container_xml)
            archive.writestr("OEBPS/content.opf", content_opf)
            archive.writestr("OEBPS/capitulo1.xhtml", capitulo1)
            archive.writestr("OEBPS/capitulo2.xhtml", capitulo2)

    def test_extracts_epub_sections_in_spine_order(self):
        with TemporaryDirectory() as folder:
            epub_path = Path(folder) / "livro.epub"
            self._create_epub(epub_path)

            result = extract_text_from_epub(str(epub_path))

        self.assertEqual(len(result), 2)

        self.assertEqual(result[0][0], 1)
        self.assertIn("Capítulo 1", result[0][1])
        self.assertIn("Primeiro conteúdo do livro.", result[0][1])

        self.assertEqual(result[1][0], 2)
        self.assertIn("Capítulo 2", result[1][1])
        self.assertIn("Segundo conteúdo do livro.", result[1][1])

    def test_extract_document_dispatches_epub(self):
        with TemporaryDirectory() as folder:
            epub_path = Path(folder) / "livro.epub"
            self._create_epub(epub_path)

            result = extract_document(str(epub_path))

        self.assertEqual(len(result), 2)
        self.assertIn("Primeiro conteúdo", result[0][1])

    def test_extract_document_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            extract_document("arquivo.xyz")

