import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings

# MIME types accepted for website media, mapped to their canonical extension.
# The storage key extension is derived from this map, never from user input.
ALLOWED_MIME_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/svg+xml": ".svg",
    "application/pdf": ".pdf",
}


class StorageResult:
    """Result of persisting a file: the unique key and its public URL."""

    __slots__ = ("storage_key", "public_url")

    def __init__(self, storage_key: str, public_url: str) -> None:
        self.storage_key = storage_key
        self.public_url = public_url


class StorageBackend(ABC):
    """Storage abstraction so the API never depends on a concrete backend.

    Backends only receive server-generated, UUID-based storage keys; user
    input never becomes a filesystem path or object key directly.
    """

    @abstractmethod
    async def save(self, storage_key: str, content: bytes) -> StorageResult:
        """Persist `content` under `storage_key` and return the public result."""

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Remove the object; missing objects are treated as success."""

    @abstractmethod
    def public_url(self, storage_key: str) -> str:
        """Return the public URL for a storage key."""


class LocalStorageBackend(StorageBackend):
    """Development backend that stores media on the local filesystem."""

    def __init__(self, root: Path) -> None:
        self.root = root

    async def save(self, storage_key: str, content: bytes) -> StorageResult:
        path = self._resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, content)
        return StorageResult(storage_key=storage_key, public_url=self.public_url(storage_key))

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
