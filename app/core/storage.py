import asyncio
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings

# MIME types accepted for website media, mapped to their canonical extension.
# The storage key extension is derived from this map, never from user input.
# image/svg+xml is intentionally absent: SVG can carry active scripts and is
# not required by the marketing site (see docs/phases/phase-08-file-media-storage.md).
ALLOWED_MIME_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "application/pdf": ".pdf",
    # Direct video uploads (e.g. demo videos for projects/solutions).
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/ogg": ".ogv",
}

# The application-level media category, stored on the Media row.
MEDIA_TYPE_IMAGE = "image"
MEDIA_TYPE_VIDEO = "video"
MEDIA_TYPE_DOCUMENT = "document"


class StorageBackend(ABC):
    """Storage abstraction so the API never depends on a concrete backend.

    Backends only receive server-generated, UUID-based storage keys; user
    input never becomes a filesystem path or object key directly.
    """

    @abstractmethod
    async def save(self, storage_key: str, content: bytes) -> None:
        """Persist `content` under `storage_key`."""

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Remove the object; missing objects are treated as success."""

    @abstractmethod
    def public_url(self, storage_key: str) -> str:
        """Return the public delivery URL for a storage key.

        The URL is always derived from the storage key and the current storage
        configuration, never persisted, so changing storage/CDN configuration
        does not require rewriting database rows.
        """


class LocalStorageBackend(StorageBackend):
    """Development backend that stores media on the local filesystem."""

    def __init__(self, root: Path) -> None:
        self.root = root

    async def save(self, storage_key: str, content: bytes) -> None:
        path = self._resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write atomically: write to a temp file in the same directory, then
        # rename into place so a partial/failed write never leaves a corrupt
        # object at the final storage key.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            await asyncio.to_thread(os.replace, tmp_name, path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    async def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    def public_url(self, storage_key: str) -> str:
        return f"/media/{storage_key}"

    def _resolve(self, storage_key: str) -> Path:
        key = Path(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise ValueError("storage key must be a safe relative path")
        return self.root / key


def build_storage_key(mime_type: str) -> str:
    """Generate a collision-resistant, UUID-based storage key.

    The key never contains user input: a random UUID plus the canonical
    extension derived from the validated MIME type.
    """
    ext = ALLOWED_MIME_TYPES[mime_type]
    return f"{uuid4().hex}{ext}"


def get_storage() -> StorageBackend:
    """Return the configured storage backend."""
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorageBackend(Path(settings.media_root))
    raise RuntimeError(f"Unsupported storage backend: {settings.storage_backend}")
