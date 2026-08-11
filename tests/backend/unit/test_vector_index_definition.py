"""Schema guard for the local MongoDB vector index."""

from scripts.build_vector_index import vector_index_definition


def test_vector_index_matches_adr_005() -> None:
    definition = vector_index_definition()

    assert definition == {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": 1536,
                "similarity": "cosine",
            }
        ]
    }
