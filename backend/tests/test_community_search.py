import asyncio
from copy import deepcopy

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
        self.cursor = FakeCursor(self.documents)
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
            "title": "Kidney care",
            "content": "A helpful post",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
        {
            "_id": "second",
            "title": "Kidney care follow-up",
            "content": "Another helpful post",
            "authorName": "Patient",
            "postType": PostType.BOARD,
            "isDeleted": False,
        },
    ])

    class FakeDatabase:
        def __getitem__(self, name):
            assert name == "posts"
            return collection

    monkeypatch.setattr(community, "db", FakeDatabase())

    result = asyncio.run(
        community.search_posts(q="kidney+care", limit=1, postType=PostType.BOARD)
    )

    assert len(result["posts"]) == 1
    assert result["posts"][0]["id"] == "first"
    assert result["hasMore"] is True
    assert collection.cursor.requested_limit == 2
    assert collection.query["isDeleted"] is False
    assert collection.query["postType"] == PostType.BOARD
    assert collection.query["$or"][0]["title"]["$regex"] == r"kidney\+care"
