"""Safe local G-code storage helpers.

Disk layout is always server-owned:
``{FILE_STORAGE_ROOT}/{user_id}/{job_id}.(gcode|gco)``.
Responses expose only the relative key under the storage root.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import settings

ALLOWED_EXTENSIONS = frozenset({".gcode", ".gco"})


def relative_storage_key(
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    extension: str,
) -> str:
    """Return the relative key stored on the Print Job (never absolute)."""
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return f"{user_id}/{job_id}{ext}"


def absolute_path_for_key(relative_key: str, *, storage_root: str | None = None) -> Path:
    """Resolve a relative key under the storage root with traversal protection."""
    root = Path(storage_root or settings.file_storage_root).resolve()
    candidate = (root / relative_key).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("storage key escapes storage root")
    return candidate


def write_bytes(relative_key: str, content: bytes, *, storage_root: str | None = None) -> Path:
    """Write upload bytes to the server-owned path; create parent dirs as needed."""
    path = absolute_path_for_key(relative_key, storage_root=storage_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def delete_if_exists(relative_key: str, *, storage_root: str | None = None) -> None:
    """Best-effort delete of an uploaded file (and empty user directory)."""
    path = absolute_path_for_key(relative_key, storage_root=storage_root)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
    parent = path.parent
    try:
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        return
