import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import re

from bson import ObjectId

from app.api import community
from app.models.community import PostType


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.requested_limit = None
        self.sort_spec = None

    def sort(self, sort_spec):
        self.sort_spec = sort_spec
        assert sort_spec == [("lastActivityAt", -1), ("_id", -1)]
        self.documents = sorted(
            self.documents,
            key=lambda document: (document["lastActivityAt"], document["_id"]),
            reverse=True,
        )
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
        if "$and" in query:
            cursor_or = query["$and"][0]["$or"]
            cursor_time = cursor_or[0]["lastActivityAt"]["$lt"]
            cursor_id = cursor_or[1]["_id"]["$lt"]
            filtered = [
                document
                for document in filtered
                if document["lastActivityAt"] < cursor_time
                or (
                    document["lastActivityAt"] == cursor_time
                    and document["_id"] < cursor_id
                )
            ]
        self.cursor = FakeCursor([document.copy() for document in filtered])
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
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "lastActivityAt": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "title": "Kidney+Care",
            "content": "A helpful post",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "lastActivityAt": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "title": "A follow-up",
            "content": "KIDNEY+CARE follow-up",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439013"),
            "lastActivityAt": datetime(2025, 12, 31, tzinfo=timezone.utc),
            "title": "A different post",
            "content": "No keyword here",
            "authorName": "Kidney+Caregiver",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439014"),
            "lastActivityAt": datetime(2025, 12, 30, tzinfo=timezone.utc),
            "title": "Kidney+Care deleted",
            "content": "Should be excluded",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": True,
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439015"),
            "lastActivityAt": datetime(2025, 12, 29, tzinfo=timezone.utc),
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
    assert result["posts"][0]["id"] == "507f1f77bcf86cd799439011"
    assert result["hasMore"] is True
    assert result["posts"][1]["id"] == "507f1f77bcf86cd799439012"
    assert result["nextCursor"]
    assert collection.cursor.sort_spec == [("lastActivityAt", -1), ("_id", -1)]
    assert collection.cursor.requested_limit == 3
    assert collection.query["isDeleted"] is False
    assert collection.query["postType"] == PostType.BOARD
    assert collection.query["$or"][0]["title"]["$regex"] == r"kidney\+care"

    next_page = asyncio.run(
        community.search_posts(
            q="kidney+care",
            limit=2,
            postType=PostType.BOARD,
            cursor=result["nextCursor"],
        )
    )
    assert [post["id"] for post in next_page["posts"]] == [
        "507f1f77bcf86cd799439013"
    ]
    assert next_page["hasMore"] is False
    assert next_page["nextCursor"] is None

    exact_result = asyncio.run(
        community.search_posts(q="KIDNEY+CARE", limit=3, postType=PostType.BOARD)
    )
    assert [post["id"] for post in exact_result["posts"]] == [
        "507f1f77bcf86cd799439011",
        "507f1f77bcf86cd799439012",
        "507f1f77bcf86cd799439013",
    ]
    assert exact_result["hasMore"] is False
    assert exact_result["nextCursor"] is None
