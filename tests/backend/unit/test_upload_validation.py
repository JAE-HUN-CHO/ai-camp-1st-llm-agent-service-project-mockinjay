"""Upload safety contract tests for community image uploads."""

import pytest

from backend.app.utils.upload import read_validated_image, validate_upload_filename


@pytest.mark.parametrize("filename", ["photo.jpg", "meal.PNG", "scan.webp"])
def test_allowed_image_extension_is_normalized(filename: str) -> None:
    assert validate_upload_filename(filename) in {".jpg", ".png", ".webp"}


@pytest.mark.parametrize("filename", ["../../secret.txt", "photo.exe", "", ".env"])
def test_invalid_or_path_like_filename_is_rejected(filename: str) -> None:
    with pytest.raises(ValueError):
        validate_upload_filename(filename)


class _Upload:
    def __init__(self, content: bytes, filename: str = "meal.jpg", content_type: str = "image/jpeg") -> None:
        self.content = content
        self.filename = filename
        self.content_type = content_type

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.content)
        chunk, self.content = self.content[:size], self.content[size:]
        return chunk


@pytest.mark.asyncio
async def test_image_reader_enforces_metadata_and_size() -> None:
    assert await read_validated_image(_Upload(b"image-bytes")) == b"image-bytes"

    with pytest.raises(ValueError, match="content type"):
        await read_validated_image(_Upload(b"image-bytes", content_type="text/plain"))

    with pytest.raises(ValueError, match="do not match"):
        await read_validated_image(_Upload(b"image-bytes", content_type="image/png"))

    with pytest.raises(ValueError, match="maximum size"):
        await read_validated_image(_Upload(b"12345"), max_bytes=4)
