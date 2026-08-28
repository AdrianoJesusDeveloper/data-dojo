import hashlib
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.db import transaction

from library.models import LibrarySource


CATALOG_EXTENSIONS = {".pdf", ".epub", ".docx", ".ipynb", ".py", ".java", ".js", ".ts", ".md"}
EXTRACTABLE_EXTENSIONS = {".pdf"}


def library_root() -> Path:
    root = settings.LOCAL_LIBRARY_PATH.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("Diretório do acervo não encontrado ou indisponível.")
    return root


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_library_file(root: Path, candidate: Path) -> Path:
    """Resolve a file fail-closed and prove containment before any file I/O."""
    canonical_root = root.expanduser().resolve(strict=True)
    unresolved = candidate if candidate.is_absolute() else canonical_root / candidate
    resolved = unresolved.resolve(strict=True)
    try:
        resolved.relative_to(canonical_root)
    except ValueError as exc:
        raise ValueError("Arquivo fora da raiz permitida.") from exc
    if not resolved.is_file():
        raise ValueError("Arquivo indisponÃ­vel.")
    return resolved


@transaction.atomic
def scan_library() -> dict:
    root = library_root()
    seen = set()
    created = updated = duplicates = 0
    hashes = {}
    existing_by_path = {item.relative_path: item for item in LibrarySource.objects.all()}

    for discovered in root.rglob("*"):
        if discovered.name.startswith("~$"):
            continue
        extension = discovered.suffix.lower()
        if extension not in CATALOG_EXTENSIONS:
            continue
        try:
            path = resolve_library_file(root, discovered)
        except (OSError, RuntimeError, ValueError):
            continue
        relative = path.relative_to(root).as_posix()
        seen.add(relative)
        stat = path.stat()
        existing = existing_by_path.get(relative)
        unchanged = (
            existing is not None
            and existing.size_bytes == stat.st_size
            and existing.modified_at is not None
            and abs(existing.modified_at.timestamp() - stat.st_mtime) < 1
            and bool(existing.sha256)
        )
        file_hash = existing.sha256 if unchanged else _sha256(path)
        if file_hash in hashes:
            duplicates += 1
        else:
            hashes[file_hash] = relative
        _, was_created = LibrarySource.objects.update_or_create(
            relative_path=relative,
            defaults={
                "filename": path.name,
                "extension": extension.lstrip("."),
                "size_bytes": stat.st_size,
                "sha256": file_hash,
                "status": "supported" if extension in EXTRACTABLE_EXTENSIONS else "unsupported",
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            },
        )
        created += int(was_created)
        updated += int(not was_created)

    missing = LibrarySource.objects.exclude(relative_path__in=seen).update(status="missing")
    return {
        "total": len(seen),
        "created": created,
        "updated": updated,
        "missing": missing,
        "duplicates": duplicates,
    }
