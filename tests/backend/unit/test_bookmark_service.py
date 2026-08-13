from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.services.mypage.bookmark_service import BookmarkService


class _ExistingBookmarkCollection:
    async def find_one(self, _query):
        return {"_id": "existing"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("item_type", "expected"),
    [("paper", "이미 북마크된 논문입니다"), ("news", "이미 북마크된 뉴스입니다")],
)
async def test_duplicate_bookmark_error_names_item_type(item_type, expected):
    service = BookmarkService()
    service._bookmarks_collection = _ExistingBookmarkCollection()

    with pytest.raises(HTTPException) as error:
        await service.add_bookmark("user-1", "item-1", {"title": "title"}, item_type=item_type)

    assert error.value.status_code == 400
    assert error.value.detail == expected
