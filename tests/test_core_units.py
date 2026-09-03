import asyncio
import re
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.api.v1.endpoints.admin_files import _safe_original_name
from app.api.v1.endpoints.common import integrity_error_response
from app.core.security import generate_session_token, hash_session_token
from app.core.storage import (
    ALLOWED_MIME_TYPES,
    LocalStorageBackend,
    StorageResult,
    build_storage_key,
    get_storage,
)
from app.schemas.files import normalize_folder

HEX_UUID = re.compile(r"^[0-9a-f]{32}$")


class _FakeOrig:
    def __init__(self, sqlstate: str | None) -> None:
        self.sqlstate = sqlstate


def _integrity(sqlstate: str | None) -> IntegrityError:
    return IntegrityError("INSERT ...", {}, _FakeOrig(sqlstate))


# --------------------------------------------------------------------------- #
# integrity_error_response mapping
# --------------------------------------------------------------------------- #
def test_integrity_unique_violation_maps_to_409() -> None:
    exc = integrity_error_response(_integrity("23505"))
    assert exc.status_code == 409


def test_integrity_fk_violation_maps_to_422() -> None:
    exc = integrity_error_response(_integrity("23503"))
    assert exc.status_code == 422


def test_integrity_not_null_violation_maps_to_422() -> None:
    exc = integrity_error_response(_integrity("23502"))
    assert exc.status_code == 422


def test_integrity_unknown_sqlstate_maps_to_500() -> None:
    exc = integrity_error_response(_integrity("XX000"))
    assert exc.status_code == 500


def test_integrity_without_orig_maps_to_500() -> None:
    exc = integrity_error_response(IntegrityError("stmt", {}, None))
    assert exc.status_code == 500


# --------------------------------------------------------------------------- #
# Storage key generation
# --------------------------------------------------------------------------- #
def test_build_storage_key_uses_mime_extension() -> None:
    for mime, ext in ALLOWED_MIME_TYPES.items():
        key = build_storage_key(mime)
        assert key.endswith(ext)
        assert HEX_UUID.fullmatch(key[:32])


def test_build_storage_keys_are_unique() -> None:
    keys = {build_storage_key("image/png") for _ in range(100)}
    assert len(keys) == 100


def test_storage_result_slots() -> None:
    result = StorageResult(storage_key="abc.png", public_url="/media/abc.png")
    assert result.storage_key == "abc.png"
    assert result.public_url == "/media/abc.png"


# --------------------------------------------------------------------------- #
# LocalStorageBackend
# --------------------------------------------------------------------------- #
def test_local_backend_save_and_public_url(tmp_path: Path) -> None:
    backend = LocalStorageBackend(tmp_path)

    async def run() -> StorageResult:
        return await backend.save("abc.png", b"data")

    result = asyncio.run(run())
    assert (tmp_path / "abc.png").read_bytes() == b"data"
    assert result.public_url == "/media/abc.png"
    assert backend.public_url("abc.png") == "/media/abc.png"


def test_local_backend_delete_removes_and_is_idempotent(tmp_path: Path) -> None:
    backend = LocalStorageBackend(tmp_path)
    (tmp_path / "abc.png").write_bytes(b"data")

    async def run() -> None:
        await backend.delete("abc.png")
        await backend.delete("abc.png")  # missing object is a no-op

    asyncio.run(run())
    assert not (tmp_path / "abc.png").exists()


@pytest.mark.parametrize("key", ["../evil.png", "/abs.png", "a/../b.png", "a/../../b.png"])
def test_local_backend_resolve_rejects_unsafe_keys(tmp_path: Path, key: str) -> None:
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(ValueError):
        backend._resolve(key)


def test_local_backend_resolve_accepts_safe_key(tmp_path: Path) -> None:
    backend = LocalStorageBackend(tmp_path)
    assert backend._resolve("sub/abc.png") == tmp_path / "sub" / "abc.png"


def test_get_storage_returns_local_backend() -> None:
    storage = get_storage()
    assert isinstance(storage, LocalStorageBackend)


def test_get_storage_unknown_backend_raises(monkeypatch) -> None:
    class _FakeSettings:
        storage_backend = "s3"
        media_root = "./media"

    monkeypatch.setattr("app.core.storage.get_settings", lambda: _FakeSettings())
    with pytest.raises(RuntimeError):
        get_storage()


# --------------------------------------------------------------------------- #
# Filename sanitization
# --------------------------------------------------------------------------- #
def test_safe_original_name_strips_paths() -> None:
    assert _safe_original_name("../../etc/passwd.png") == "passwd.png"
    assert _safe_original_name("C:\\Users\\x\\file.jpg") == "file.jpg"
    assert _safe_original_name("/absolute/path/x.gif") == "x.gif"


def test_safe_original_name_strips_nul_and_truncates() -> None:
    assert _safe_original_name("a\x00b.png") == "ab.png"
    long_name = "x" * 300 + ".png"
    assert len(_safe_original_name(long_name)) == 255


def test_safe_original_name_default_and_blank() -> None:
    assert _safe_original_name(None) == "file"
    assert _safe_original_name("") == "file"
    assert _safe_original_name("   ") == "file"


# --------------------------------------------------------------------------- #
# Session token helpers
# --------------------------------------------------------------------------- #
def test_hash_session_token_is_deterministic_hex() -> None:
    h1 = hash_session_token("abc")
    h2 = hash_session_token("abc")
    assert h1 == h2
    assert len(h1) == 64
    int(h1, 16)  # valid hex


def test_generate_session_token_unique_and_urlsafe() -> None:
    tokens = {generate_session_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(len(t) >= 32 for t in tokens)


# --------------------------------------------------------------------------- #
# Folder name normalization
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value", ["projects", "case-studies", "a_b", None])
def test_normalize_folder_valid(value) -> None:
    assert normalize_folder(value) == value


@pytest.mark.parametrize("value", ["has space", "../x", "UPPER", "a/b", "", "x" * 101])
def test_normalize_folder_invalid(value) -> None:
    with pytest.raises(ValueError):
        normalize_folder(value)
