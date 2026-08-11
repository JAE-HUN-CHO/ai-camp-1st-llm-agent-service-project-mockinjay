"""Upload safety contract tests for community image uploads."""

import pytest

from backend.app.utils.upload import validate_upload_filename


@pytest.mark.parametrize("filename", ["photo.jpg", "meal.PNG", "scan.webp"])
def test_allowed_image_extension_is_normalized(filename: str) -> None:
    assert validate_upload_filename(filename) in {".jpg", ".png", ".webp"}


@pytest.mark.parametrize("filename", ["../../secret.txt", "photo.exe", "", ".env"])
def test_invalid_or_path_like_filename_is_rejected(filename: str) -> None:
    with pytest.raises(ValueError):
        validate_upload_filename(filename)
