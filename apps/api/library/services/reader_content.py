"""Bounded, inert EPUB/DOCX conversion. No archive extraction or remote resources."""
import html as escape_html
import posixpath
import zipfile
from pathlib import Path
from urllib.parse import unquote

from lxml import etree, html

ALLOWED = {"p", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "strong", "b", "em", "i", "u", "blockquote", "pre", "code", "br", "hr", "table", "thead", "tbody", "tr", "td", "th", "sup", "sub", "a"}


def sanitize_html(value):
    root = html.fragment_fromstring(value or "<p></p>", create_parent="div")
    for node in list(root.iterdescendants()):
        if not isinstance(node.tag, str):
            node.drop_tree()
            continue
        tag = node.tag.lower().split("}")[-1]
        if tag in {"script", "style", "iframe", "object", "embed", "svg", "math", "form", "input", "link", "meta", "base"}:
            node.drop_tree()
            continue
        attrs = dict(node.attrib)
        node.attrib.clear()
        if tag not in ALLOWED:
            node.drop_tag()
            continue
        node.tag = tag
        if attrs.get("id"):
            node.set("id", attrs["id"][:200])
        href = attrs.get("href", "")
        if tag == "a" and href and not any(c in href for c in (":", "\\")) and not href.startswith("/"):
            node.set("data-reader-href", href[:500])
    return "".join(html.tostring(child, encoding="unicode") for child in root), root.text_content()


def archive_read(archive, name):
    name = unquote(name).split("#")[0]
    normalized = posixpath.normpath(name)
    if normalized.startswith(("../", "/")) or "\\" in normalized:
        raise ValueError("Caminho inválido no documento.")
    info = archive.getinfo(normalized)
    if info.file_size > 20 * 1024 * 1024:
        raise ValueError("Seção excede o limite de leitura.")
    return archive.read(info)


def epub_package(archive):
    if sum(item.file_size for item in archive.infolist()) > 150 * 1024 * 1024:
        raise ValueError("EPUB excede o limite de conteúdo descompactado.")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    container = etree.fromstring(archive_read(archive, "META-INF/container.xml"), parser)
    opf = container.xpath("//*[local-name()='rootfile']/@full-path")[0]
    root = etree.fromstring(archive_read(archive, opf), parser)
    manifest = {node.get("id"): node for node in root.xpath("//*[local-name()='manifest']/*[local-name()='item']")}
    return opf, root, manifest


def epub_sections(path):
    with zipfile.ZipFile(path) as archive:
        opf, root, manifest = epub_package(archive)
        result = []
        for position, ref in enumerate(root.xpath("//*[local-name()='spine']/*[local-name()='itemref']/@idref"), 1):
            item = manifest.get(ref)
            if item is None or item.get("media-type") not in {"application/xhtml+xml", "text/html"}:
                continue
            location = posixpath.normpath(posixpath.join(posixpath.dirname(opf), unquote(item.get("href"))))
            raw = archive_read(archive, location).decode("utf-8-sig", errors="replace")
            document = html.fromstring(raw)
            body = document.find(".//body")
            safe, text = sanitize_html(html.tostring(body if body is not None else document, encoding="unicode"))
            headings = document.xpath("//h1//text()|//h2//text()|//title//text()")
            result.append(dict(position=position, location=location, title=" ".join(headings)[:500] or f"Capítulo {position}", text=text, html=safe))
        if not result:
            raise ValueError("Nenhum texto foi extraído do EPUB.")
        return result


def flow_sections(path):
    extension = Path(path).suffix.lower()
    if extension == ".epub":
        return epub_sections(path)
    if extension == ".txt":
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace").replace("\x00", "")
        pieces = [text[index:index + 12000] for index in range(0, len(text), 12000)]
        return [dict(position=i, location=f"text:{i}", title=f"Trecho {i}", text=value, html="") for i, value in enumerate(pieces, 1)]
    if extension == ".docx":
        from docx import Document
        from docx.text.paragraph import Paragraph
        from docx.table import Table
        with zipfile.ZipFile(path) as archive:
            if sum(item.file_size for item in archive.infolist()) > 150 * 1024 * 1024:
                raise ValueError("DOCX excede o limite de conteúdo descompactado.")
        document = Document(path)
        groups, fragments, title = [], [], "Início"
        def flush():
            if fragments:
                safe, text = sanitize_html("".join(fragments))
                n = len(groups) + 1
                groups.append(dict(position=n, location=f"section:{n}", title=title[:500], text=text, html=safe))
                fragments.clear()
        for element in document.element.body:
            if element.tag.endswith("}p"):
                paragraph = Paragraph(element, document)
                heading = paragraph.style.name.startswith("Heading") if paragraph.style else False
                if heading:
                    flush()
                    title = paragraph.text or "Seção"
                runs = []
                for run in paragraph.runs:
                    value = escape_html.escape(run.text).replace("\n", "<br>")
                    if run.bold:
                        value = f"<strong>{value}</strong>"
                    if run.italic:
                        value = f"<em>{value}</em>"
                    runs.append(value)
                tag = "h2" if heading else "p"
                value = "".join(runs)
                if paragraph.style and "List" in paragraph.style.name:
                    value = f"<ul><li>{value}</li></ul>"
                fragments.append(f"<{tag}>{value}</{tag}>")
            elif element.tag.endswith("}tbl"):
                table = Table(element, document)
                fragments.append("<table>" + "".join("<tr>" + "".join(f"<td>{escape_html.escape(cell.text)}</td>" for cell in row.cells) + "</tr>" for row in table.rows) + "</table>")
        flush()
        return groups
    return []
