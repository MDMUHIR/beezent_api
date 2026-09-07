"""Tiny, valid media fixtures used by the upload tests.

Images are generated with Pillow so they are genuinely decodable; videos and
PDFs carry the correct container magic bytes (validation checks signatures,
not full playback).
"""

from __future__ import annotations

import io

from PIL import Image


def _encode_image(fmt: str, size: tuple[int, int], color: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


PNG = _encode_image("PNG", (16, 9), "red")
JPEG = _encode_image("JPEG", (16, 9), "red")
GIF = _encode_image("GIF", (16, 9), "red")
WEBP = _encode_image("WEBP", (16, 9), "red")
AVIF = _encode_image("AVIF", (16, 9), "red")

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"

# Minimal valid container signatures (not full videos).
MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41" + b"\x00" * 16
MOV = b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00qt  " + b"\x00" * 16
WEBM = b"\x1a\x45\xdf\xa3\x01\x00\x00\x00\x00\x00\x00\x00\x1f\x42\x86\x81\x01" + b"\x00" * 16
OGV = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x00" * 16
