"""Regression tests ensuring user-facing routes never fabricate product data."""

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api import news
from app.api.bookmarks import _serialize_bookmark


@pytest.mark.asyncio
async def test_news_list_reports_provider_failure_instead_of_mock_data(monkeypatch):
    monkeypatch.setattr(news, "GNEWS_API_KEY", "")
    monkeypatch.setattr(news, "NEWSDATA_API_KEY", "")
    monkeypatch.setattr(news, "get_cached_news", lambda *_args: None)

    async def empty_rss(_language):
        return []

    monkeypatch.setattr(news, "fetch_all_rss_feeds", empty_rss)

    with pytest.raises(HTTPException) as error:
        await news.get_news_list(news.NewsRequest(language="en", source="auto"))

    assert error.value.status_code == 503
    assert "뉴스 제공자" in str(error.value.detail)


def test_bookmark_serializer_preserves_real_paper_metadata():
    serialized = _serialize_bookmark({
        "id": "bookmark-1",
        "userId": "user-1",
        "itemType": "paper",
        "itemId": "pmid-1",
        "itemData": {"title": "A real paper", "authors": ["Author"]},
        "createdAt": "2026-08-12T00:00:00Z",
    })

    assert serialized["paperId"] == "pmid-1"
    assert serialized["title"] == "A real paper"
    assert serialized["authors"] == ["Author"]
