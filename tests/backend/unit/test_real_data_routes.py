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


def test_bookmark_serializer_preserves_news_metadata():
    serialized = _serialize_bookmark({
        "id": "bookmark-news-1",
        "userId": "user-1",
        "itemType": "news",
        "itemId": "article-1",
        "itemData": {"title": "A real article", "source": "RSS"},
        "createdAt": "2026-08-12T00:00:00Z",
    })

    assert serialized["itemId"] == "article-1"
    assert serialized["itemData"]["title"] == "A real article"


def test_bookmark_serializer_supports_legacy_paper_shape():
    serialized = _serialize_bookmark({
        "_id": "legacy-1",
        "userId": "user-1",
        "paperId": "pmid-legacy",
        "paperData": {"title": "Legacy paper", "authors": ["Legacy Author"]},
    })

    assert serialized["paperId"] == "pmid-legacy"
    assert serialized["title"] == "Legacy paper"


def test_bookmark_serializer_preserves_explicit_empty_updates():
    serialized = _serialize_bookmark({
        "id": "bookmark-2",
        "itemType": "paper",
        "itemId": "pmid-2",
        "itemData": {"tags": ["legacy"], "notes": "legacy"},
        "tags": [],
        "notes": "",
    })

    assert serialized["tags"] == []
    assert serialized["notes"] == ""
