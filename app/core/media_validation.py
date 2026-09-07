"""Application-level upload validation boundary.

This module validates an uploaded byte stream against its *declared* MIME type
before anything is persisted. It is a deliberate, lightweight validation
boundary - not an antivirus pipeline. It checks:

* file signature / actual content (via Pillow for images, magic bytes for
  videos and PDFs) so a client-declared Content-Type is not trusted blindly;
* that an image actually decodes and reports the dimensions;
* that the generated storage extension can be derived safely.

What remains outside the backend's responsibility (documented in the phase
report): deep malware scanning, sanitizing archive bombs, video re-encoding,
and validating every byte of a video stream (videos are checked by container
signature only - `duration_seconds` stays NULL for direct uploads).
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.core.storage import ALLOWED_MIME_TYPES

# Pillow format name -> declared MIME type it is allowed to satisfy.
_PILLOW_FORMAT_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
    "AVIF": "image/avif",
}

# Container magic bytes for the allowed non-image uploads.
_PDF_MAGIC = b"%PDF-"
_EBML_MAGIC = b"\x1a\x45\xdf\xa3"  # WebM / Matroska
_OGG_MAGIC = b"OggS"


class MediaValidationError(ValueError):
    """Raised when an upload's declared MIME type does not match its content."""


@dataclass(slots=True)
class InspectedMedia:
    """Result of validating and inspecting an upload's byte stream."""

    media_type: str
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None


def media_type_from_mime(mime_type: str) -> str:
    """Return the coarse media category for a MIME type."""
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type == "application/pdf":
        return "document"
    raise MediaValidationError("Unsupported media type")


def inspect_upload(mime_type: str, content: bytes) -> InspectedMedia:
    """Validate `content` against the declared `mime_type`.

    Raises :class:`MediaValidationError` when the content does not match the
    declared type. Returns dimensions for images; video duration is not
    extracted (no FFmpeg dependency) and remains ``None``.
    """
    if mime_type not in ALLOWED_MIME_TYPES:
        raise MediaValidationError("Unsupported file type")

    media_type = media_type_from_mime(mime_type)
    if media_type == "image":
        return _inspect_image(mime_type, content)
    if media_type == "video":
        return _inspect_video(mime_type, content)
    return _inspect_document(content)


def _inspect_image(mime_type: str, content: bytes) -> InspectedMedia:
    if not content:
        raise MediaValidationError("Image file is empty")
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            detected = _PILLOW_FORMAT_TO_MIME.get(image.format or "")
    except UnidentifiedImageError as exc:
        raise MediaValidationError("File content does not match an image") from exc
    except OSError as exc:
        raise MediaValidationError("File content is not a valid image") from exc

    if detected != mime_type:
        raise MediaValidationError("File content does not match the declared image type")
    return InspectedMedia(media_type="image", width=image.width, height=image.height)


def _inspect_video(mime_type: str, content: bytes) -> InspectedMedia:
    if len(content) < 8:
        raise MediaValidationError("Video file is too small to be valid")

    if mime_type in ("video/mp4", "video/quicktime"):
        # MP4 / QuickTime (and HEIC-style) containers start with an ISO BMFF
        # "ftyp" box at offset 4.
        if content[4:8] != b"ftyp":
            raise MediaValidationError("File content is not a valid MP4/QuickTime container")
    elif mime_type == "video/webm":
        if not content.startswith(_EBML_MAGIC):
            raise MediaValidationError("File content is not a valid WebM container")
    elif mime_type == "video/ogg":
        if not content.startswith(_OGG_MAGIC):
            raise MediaValidationError("File content is not a valid Ogg container")

    # Duration is intentionally not extracted (no FFmpeg/ffprobe dependency).
    return InspectedMedia(media_type="video", duration_seconds=None)


def _inspect_document(content: bytes) -> InspectedMedia:
    if not content.startswith(_PDF_MAGIC):
        raise MediaValidationError("File content is not a valid PDF")
    return InspectedMedia(media_type="document")
