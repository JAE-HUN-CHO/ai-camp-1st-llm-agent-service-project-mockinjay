import os

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError


@pytest.mark.integration
def test_local_mongo_vector_index_is_queryable():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI is required for the live Mongo integration smoke")

    database_name = os.getenv("DB_NAME", "careguide")
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
        indexes = list(client[database_name].pubmed_embeddings.list_search_indexes())
    except PyMongoError as exc:  # pragma: no cover - environment-specific failure
        pytest.fail(f"local MongoDB/vector index smoke failed: {exc}")
    finally:
        client.close()

    vector_index = next((item for item in indexes if item.get("name") == "vector_index"), None)
    assert vector_index is not None
    assert vector_index["type"] == "vectorSearch"
    assert vector_index["status"] == "READY"
    assert vector_index["queryable"] is True
    assert vector_index["latestDefinition"]["fields"][0]["numDimensions"] == 1536
