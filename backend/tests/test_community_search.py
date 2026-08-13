import asyncio
from copy import deepcopy
import re

from app.api import community
from app.models.community import PostType


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.requested_limit = None

    def sort(self, *_args):
        return self

    def limit(self, value):
        self.requested_limit = value
        return self

    async def to_list(self, length):
        assert length == self.requested_limit
        return deepcopy(self.documents[:length])


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents
        self.query = None
        self.cursor = None

    def find(self, query):
        self.query = query
        pattern = query["$or"][0]["title"]["$regex"]
        post_type = query.get("postType")
        filtered = [
            document
            for document in self.documents
            if not document["isDeleted"]
            and (post_type is None or document["postType"] == post_type)
            and any(
                re.search(pattern, document[field], re.IGNORECASE)
                for field in ("title", "content", "authorName")
            )
        ]
        self.cursor = FakeCursor(filtered)
        return self.cursor


def test_community_search_route_is_registered():
    routes = {
        (route.path, method)
        for route in community.router.routes
        for method in route.methods
    }

    assert ("/search", "GET") in routes


def test_community_search_filters_and_paginates(monkeypatch):
    collection = FakeCollection([
        {
            "_id": "first",
            "title": "Kidney+Care",
            "content": "A helpful post",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
        {
            "_id": "second",
            "title": "A follow-up",
            "content": "KIDNEY+CARE follow-up",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
        {
            "_id": "third",
            "title": "A different post",
            "content": "No keyword here",
            "authorName": "Kidney+Caregiver",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
        {
            "_id": "deleted",
            "title": "Kidney+Care deleted",
            "content": "Should be excluded",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": True,
        },
        {
            "_id": "other-type",
            "title": "Kidney+Care survey",
            "content": "Should be filtered by type",
            "authorName": "Patient",
            "postType": PostType.SURVEY,
            "isDeleted": False,
        },
    ])

    class FakeDatabase:
        def __getitem__(self, name):
            assert name == "posts"
            return collection

    monkeypatch.setattr(community, "db", FakeDatabase())

    result = asyncio.run(
        community.search_posts(q="kidney+care", limit=2, postType=PostType.BOARD)
    )

    assert len(result["posts"]) == 2
    assert result["posts"][0]["id"] == "first"
    assert result["hasMore"] is True
    assert result["posts"][1]["id"] == "second"
    assert collection.cursor.requested_limit == 3
    assert collection.query["isDeleted"] is False
    assert collection.query["postType"] == PostType.BOARD
    assert collection.query["$or"][0]["title"]["$regex"] == r"kidney\+care"

    exact_result = asyncio.run(
        community.search_posts(q="KIDNEY+CARE", limit=3, postType=PostType.BOARD)
    )
    assert [post["id"] for post in exact_result["posts"]] == ["first", "second"]
    assert exact_result["hasMore"] is False
