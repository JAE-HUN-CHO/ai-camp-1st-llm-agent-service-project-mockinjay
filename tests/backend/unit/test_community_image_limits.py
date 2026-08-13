import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.models.community import PostCreate, PostType, PostUpdate


def _post_payload(image_urls):
    return {
        "title": "Test post",
        "content": "Content",
        "postType": PostType.BOARD,
        "imageUrls": image_urls,
    }


def test_post_image_urls_are_limited_to_five_items():
    with pytest.raises(ValidationError):
        PostCreate(**_post_payload(["/uploads/image.jpg"] * 6))
    with pytest.raises(ValidationError):
        PostUpdate(imageUrls=["/uploads/image.jpg"] * 6)


def test_post_image_url_length_is_bounded_for_create_and_update():
    long_url = "https://example.com/" + ("a" * 2048)
    with pytest.raises(ValidationError):
        PostCreate(**_post_payload([long_url]))
    with pytest.raises(ValidationError):
        PostUpdate(imageUrls=[long_url])
