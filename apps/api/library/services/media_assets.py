import hashlib
import io
import posixpath
import zipfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from library.models import Book, MediaAsset
from .book_storage import book_path
from .reader_content import epub_package, archive_read

IMAGE_TYPES = {"PNG": ("image/png", {".png"}), "JPEG": ("image/jpeg", {".jpg", ".jpeg"}), "WEBP": ("image/webp", {".webp"})}


def create_asset(upload, user=None, category="OTHER", source_type="upload", title=""):
    if category not in dict(MediaAsset.CATEGORIES):
        raise ValidationError("Categoria inválida.")
    if upload.size > 10 * 1024 * 1024:
        raise ValidationError("A imagem deve ter no máximo 10 MB.")
    data = upload.read()
    upload.seek(0)
    try:
        with Image.open(io.BytesIO(data)) as image:
            fmt, dimensions = image.format, image.size
            if fmt not in IMAGE_TYPES or dimensions[0] * dimensions[1] > 25_000_000:
                raise ValueError()
            mime, extensions = IMAGE_TYPES[fmt]
            if Path(upload.name).suffix.lower() not in extensions:
                raise ValueError()
            if getattr(upload, "content_type", mime) != mime:
                raise ValueError()
            image.verify()
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValidationError("Envie uma imagem PNG, JPEG ou WEBP válida, com extensão e MIME correspondentes.") from exc
    digest = hashlib.sha256(data).hexdigest()
    existing = MediaAsset.objects.filter(sha256=digest).first()
    if existing:
        return existing
    asset = MediaAsset(title=(title or Path(upload.name).stem)[:255], original_filename=Path(upload.name).name[:255], mime_type=mime, file_size=len(data), width=dimensions[0], height=dimensions[1], sha256=digest, category=category, source_type=source_type, created_by=user)
    asset.file.save(f"{digest}{Path(upload.name).suffix.lower()}", ContentFile(data), save=False)
    try:
        with transaction.atomic():
            asset.save()
    except IntegrityError:
        asset.file.delete(save=False)
        return MediaAsset.objects.get(sha256=digest)
    return asset


def generate_cover(book):
    if book.cover_asset_id:
        return book.cover_asset
    path = book_path(book)
    if path.suffix.lower() == ".pdf":
        import pymupdf
        with pymupdf.open(path) as document:
            if not len(document):
                return None
            page = document[0]
            scale = min(480 / max(page.rect.width, 1), 1)
            data = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")
        upload = ContentFile(data, name="cover.png")
    elif path.suffix.lower() == ".epub":
        with zipfile.ZipFile(path) as archive:
            opf, root, manifest = epub_package(archive)
            cover_id = root.xpath("//*[local-name()='meta' and @name='cover']/@content")
            cover = next((item for key, item in manifest.items() if "cover-image" in item.get("properties", "").split() or key in cover_id), None)
            if cover is None:
                return None
            name = posixpath.normpath(posixpath.join(posixpath.dirname(opf), cover.get("href")))
            upload = ContentFile(archive_read(archive, name), name=Path(name).name)
    else:
        return None
    asset = create_asset(upload, category="BOOK_COVER", source_type="extracted", title=book.title)
    Book.objects.filter(pk=book.pk, cover_asset__isnull=True).update(cover_asset=asset)
    return asset
