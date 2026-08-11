"""Create the ADR-005 MongoDB Atlas Local vector index idempotently.

The script only provisions the index definition. Embedding generation remains
owned by a separate provider adapter and must not be confused with this schema
operation.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from pymongo import MongoClient

VECTOR_INDEX_NAME = "vector_index"
VECTOR_COLLECTION = "pubmed_embeddings"
VECTOR_FIELD = "embedding"
VECTOR_DIMENSIONS = 1536


def vector_index_definition() -> dict[str, Any]:
    return {
        "fields": [
            {
                "type": "vector",
                "path": VECTOR_FIELD,
                "numDimensions": VECTOR_DIMENSIONS,
                "similarity": "cosine",
            }
        ]
    }


def ensure_vector_index(uri: str, database_name: str, *, dry_run: bool = False) -> str:
    if not uri.startswith("mongodb://"):
        raise ValueError("ADR-005 setup requires a local mongodb:// URI")

    if dry_run:
        return f"{database_name}.{VECTOR_COLLECTION}:{VECTOR_INDEX_NAME}"

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        database = client[database_name]
        if VECTOR_COLLECTION not in database.list_collection_names():
            database.create_collection(VECTOR_COLLECTION)
        collection = database[VECTOR_COLLECTION]
        existing = {item["name"] for item in collection.list_search_indexes()}
        if VECTOR_INDEX_NAME in existing:
            return f"{database_name}.{VECTOR_COLLECTION}:{VECTOR_INDEX_NAME} (already exists)"

        database.command(
            {
                "createSearchIndexes": VECTOR_COLLECTION,
                "indexes": [
                    {
                        "name": VECTOR_INDEX_NAME,
                        "type": "vectorSearch",
                        "definition": vector_index_definition(),
                    }
                ],
            }
        )
        return f"{database_name}.{VECTOR_COLLECTION}:{VECTOR_INDEX_NAME} (created)"
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uri",
        default=os.getenv(
            "MONGODB_URI",
            "mongodb://careguide:careguide_local@localhost:27017/?authSource=admin",
        ),
    )
    parser.add_argument("--db", default=os.getenv("DB_NAME", "careguide"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(ensure_vector_index(args.uri, args.db, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
