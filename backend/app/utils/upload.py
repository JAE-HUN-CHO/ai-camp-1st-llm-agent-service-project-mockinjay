"""Shared upload validation rules for user-provided files."""

from pathlib import Path
from typing import Protocol

ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})
ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)
IMAGE_CONTENT_TYPES_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class AsyncUpload(Protocol):
    filename: str | None
    content_type: str | None

    async def read(self, size: int = -1) -> bytes: ...


def validate_upload_filename(filename: str | None) -> str:
    """Return a safe normalized extension or raise for an unsafe filename."""

    raw_name = (filename or "").strip()
    basename = Path(raw_name).name
    if not raw_name or basename != raw_name or raw_name in {".", ".."}:
        raise ValueError("filename must be a simple basename")

    extension = Path(basename).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("unsupported image extension")
    return extension


async def read_validated_image(
    upload: AsyncUpload,
    *,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> bytes:
    """Validate metadata and read an image without exceeding the memory cap."""

    extension = validate_upload_filename(upload.filename)
    if max_bytes <= 0:
        raise ValueError("maximum image size must be positive")
    if upload.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValueError("unsupported image content type")
    if upload.content_type != IMAGE_CONTENT_TYPES_BY_EXTENSION[extension]:
        raise ValueError("image extension and content type do not match")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(min(1024 * 1024, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("image exceeds maximum size")
        chunks.append(chunk)

    if not chunks:
        raise ValueError("image is empty")
    return b"".join(chunks)
