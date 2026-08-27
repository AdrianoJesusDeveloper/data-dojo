import re


def extract_text_by_page(pdf_path: str) -> list[tuple[int, str]]:
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

    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = re.sub(r"[ \t]+", " ", page.extract_text() or "")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            pages.append((page_number, text))
    if not pages:
        raise ValueError("Nenhum texto foi extraído do PDF; ele pode conter apenas imagens.")
    return pages


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def chunk_text(pages: list[tuple[int, str]], chunk_size=700, overlap=100) -> list[dict]:
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
            chunks.append({
                "content": content,
                "page_number": page_number,
                "chunk_index": len(chunks),
            })
            if start + chunk_size >= len(words):
                break
    return chunks
