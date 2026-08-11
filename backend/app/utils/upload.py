"""Shared upload validation rules for user-provided files."""

from pathlib import Path

ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})


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
