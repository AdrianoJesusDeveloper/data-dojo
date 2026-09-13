import posixpath
import zipfile
import os
import re
import shutil
from pathlib import Path


def _normalize_text(text: str) -> str:
    text = (text or "").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _extract_with_pypdf(pdf_path: str) -> list[tuple[int, str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Instale a dependência pypdf para processar livros.") from exc

    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError("PDF protegido por senha não pode ser processado.") from exc

    pages: list[tuple[int, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = _normalize_text(page.extract_text() or "")
        if text:
            pages.append((page_number, text))

    return pages


def _extract_with_ocr(pdf_path: str) -> list[tuple[int, str]]:
    """
    Fallback para PDFs digitalizados/escaneados.

    Dependências Python:
      pip install pymupdf pytesseract pillow

    O executável Tesseract OCR também precisa estar instalado no Windows
    e disponível no PATH.
    """
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError(
            "O PDF parece ser digitalizado. Instale o fallback OCR com "
            "'pip install pymupdf pytesseract pillow'."
        ) from exc

    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "O PDF parece ser digitalizado. Instale o fallback OCR com "
            "'pip install pymupdf pytesseract pillow'."
        ) from exc

    tesseract_cmd = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

    pages: list[tuple[int, str]] = []

    try:
        document = pymupdf.open(pdf_path)
    except Exception as exc:
        raise ValueError("Não foi possível abrir o PDF para OCR.") from exc

    try:
        for page_number, page in enumerate(document, start=1):
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            try:
                text = pytesseract.image_to_string(image, lang="por+eng")
            except pytesseract.TesseractNotFoundError as exc:
                raise RuntimeError(
                    "O PDF parece ser digitalizado, mas o executável Tesseract OCR "
                    "não foi encontrado no sistema. Instale o Tesseract e adicione-o ao PATH."
                ) from exc
            except pytesseract.TesseractError:
                text = pytesseract.image_to_string(image)

            text = _normalize_text(text)
            if text:
                pages.append((page_number, text))
    finally:
        document.close()

    return pages

def extract_text_from_epub(epub_path: str) -> list[tuple[int, str]]:
    """
    Extrai o conteúdo textual de um EPUB respeitando a ordem de leitura
    definida pelo spine do arquivo.

    O EPUB é tratado como um pacote ZIP. Nenhum arquivo é extraído para
    o sistema de arquivos.
    """
    try:
        from lxml import etree, html
    except ImportError as exc:
        raise RuntimeError(
            "Instale a dependência lxml para processar arquivos EPUB."
        ) from exc

    epub_path_obj = Path(epub_path)

    if not epub_path_obj.exists():
        raise FileNotFoundError(f"Arquivo EPUB não encontrado: {epub_path}")

    try:
        archive = zipfile.ZipFile(epub_path_obj)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("Não foi possível abrir o arquivo EPUB.") from exc

    with archive:
        try:
            container_xml = archive.read("META-INF/container.xml")
        except KeyError as exc:
            raise ValueError(
                "EPUB inválido: META-INF/container.xml não encontrado."
            ) from exc

        try:
            container_root = etree.fromstring(container_xml)

            rootfiles = container_root.xpath(
                "//*[local-name()='rootfile']/@full-path"
            )

            if not rootfiles:
                raise ValueError(
                    "EPUB inválido: arquivo OPF principal não encontrado."
                )

            opf_path = rootfiles[0]
            opf_xml = archive.read(opf_path)
            opf_root = etree.fromstring(opf_xml)

        except (etree.XMLSyntaxError, KeyError) as exc:
            raise ValueError(
                "EPUB inválido: estrutura de metadados não pôde ser lida."
            ) from exc

        manifest = {}

        for item in opf_root.xpath("//*[local-name()='manifest']/*[local-name()='item']"):
            item_id = item.get("id")
            href = item.get("href")
            media_type = item.get("media-type", "")

            if item_id and href:
                manifest[item_id] = {
                    "href": href,
                    "media_type": media_type,
                }

        spine = opf_root.xpath(
            "//*[local-name()='spine']/*[local-name()='itemref']/@idref"
        )

        opf_directory = posixpath.dirname(opf_path)

        sections: list[tuple[int, str]] = []

        for section_number, item_id in enumerate(spine, start=1):
            manifest_item = manifest.get(item_id)

            if not manifest_item:
                continue

            media_type = manifest_item["media_type"]

            if media_type not in {
                "application/xhtml+xml",
                "text/html",
            }:
                continue

            document_path = posixpath.normpath(
                posixpath.join(
                    opf_directory,
                    manifest_item["href"],
                )
            )

            try:
                document_bytes = archive.read(document_path)
            except KeyError:
                continue

            try:
                parser = html.HTMLParser(encoding="utf-8")
                document = html.fromstring(document_bytes, parser=parser)
            except (etree.ParserError, ValueError):
                continue

            for unwanted in document.xpath("//script|//style|//noscript"):
                parent = unwanted.getparent()
                if parent is not None:
                    parent.remove(unwanted)

            text = _normalize_text(document.text_content())

            if text:
                sections.append((section_number, text))

        if sections:
            return sections

    raise ValueError("Nenhum texto foi extraído do EPUB.")

def extract_document(document_path: str) -> list[tuple[int, str]]:
    extension = Path(document_path).suffix.lower()

    if extension == ".pdf":
        return extract_text_by_page(document_path)

    if extension == ".epub":
        return extract_text_from_epub(document_path)

    raise ValueError(
        f"Formato de documento ainda não suportado: {extension or 'sem extensão'}"
    )

def extract_text_by_page(pdf_path: str) -> list[tuple[int, str]]:
    """
    Extrai texto página a página:
    1. usa pypdf nas páginas com camada de texto;
    2. usa OCR apenas nas páginas sem texto extraível.

    Isso permite processar PDFs mistos sem aplicar OCR
    desnecessariamente às páginas que já possuem texto.
    """
    pypdf_pages = _extract_with_pypdf(pdf_path)
    text_by_page = dict(pypdf_pages)

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Instale a dependência pypdf para processar livros.") from exc

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    missing_pages = {
        page_number
        for page_number in range(1, total_pages + 1)
        if page_number not in text_by_page
    }

    if missing_pages:
        ocr_pages = _extract_with_ocr(pdf_path)
        for page_number, text in ocr_pages:
            if page_number in missing_pages:
                text_by_page[page_number] = text

    pages = sorted(text_by_page.items())

    if pages:
        return pages

    raise ValueError(
        "Nenhum texto foi extraído do PDF, mesmo após a tentativa de OCR."
    )


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def chunk_text(
    pages: list[tuple[int, str]],
    chunk_size: int = 700,
    overlap: int = 100,
) -> list[dict]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size deve ser positivo e overlap menor que chunk_size.")

    chunks = []
    step = chunk_size - overlap

    for page_number, text in pages:
        words = _words(text)

        for start in range(0, len(words), step):
            content = " ".join(words[start : start + chunk_size]).strip()
            if not content:
                continue

            chunks.append(
                {
                    "content": content,
                    "page_number": page_number,
                    "chunk_index": len(chunks),
                }
            )

            if start + chunk_size >= len(words):
                break

    return chunks
