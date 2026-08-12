"""Embed structured CareGuide MongoDB data into the local vector collection.

The command is resumable and idempotent: a vector is keyed by its source
collection and source document id, so interrupted runs can be started again
without duplicating vectors.  It uses the repository's Ollama adapter, which
enforces the accepted 1536-dimensional vector contract.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path
from typing import Any

from pymongo import MongoClient, UpdateOne

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.adapters.ollama.embedding import OllamaEmbeddingProvider

DEFAULT_URI = "mongodb://careguide:careguide_local@127.0.0.1:27017/?authSource=admin&directConnection=true"
DEFAULT_COLLECTIONS = (
    "papers_kidney",
    "medical_kidney",
    "qa_kidney",
    "guidelines_kidney",
    "nutrition_foods",
)
VECTOR_COLLECTION = "pubmed_embeddings"
VECTOR_DIMENSIONS = 1536


def source_text(collection: str, document: dict[str, Any], max_chars: int) -> str:
    """Build the searchable text while retaining useful source context."""
    if collection == "papers_kidney":
        title = str(document.get("title") or "").strip()
        abstract = str(document.get("abstract") or "").strip()
        text = f"{title}\n\n{abstract}".strip()
    elif collection == "qa_kidney":
        text = f"질문: {document.get('question') or ''}\n답변: {document.get('answer') or ''}".strip()
    elif collection == "guidelines_kidney":
        text = str(document.get("raw_text") or document.get("text") or "").strip()
    elif collection == "nutrition_foods":
        labels = [
            f"{key}: {value}"
            for key, value in document.items()
            if key not in {"_id", "food_hash", "ingest_source"} and value not in (None, "")
        ]
        text = "\n".join(labels).strip()
    else:
        text = str(document.get("text") or document.get("raw_text") or "").strip()
    return text[:max_chars]


def stable_vector_id(collection: str, source_id: Any) -> str:
    value = f"{collection}:{source_id}"
    return "rag:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def vector_document(collection: str, document: dict[str, Any], text: str, embedding: list[float]) -> dict[str, Any]:
    source_id = str(document.get("_id", ""))
    metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
    return {
        "_id": stable_vector_id(collection, source_id),
        "embedding": embedding,
        "text": text,
        "chunk_text": text,
        "title": document.get("title") or metadata.get("title") or document.get("식품명") or collection,
        "abstract": document.get("abstract", ""),
        "source": document.get("source") or document.get("ingest_source") or collection,
        "metadata": {
            "collection": collection,
            "source_collection": collection,
            "source_id": source_id,
            "category": document.get("category"),
            "source_dataset": document.get("source_dataset"),
            "ingest_source": document.get("ingest_source"),
        },
    }


def existing_ids(collection, ids: list[str]) -> set[str]:
    if not ids:
        return set()
    rows = collection.find({"_id": {"$in": ids}}, {"_id": 1, "embedding": 1})
    return {
        row["_id"]
        for row in rows
        if isinstance(row.get("embedding"), list) and len(row["embedding"]) == VECTOR_DIMENSIONS
    }


async def embed_collection(
    database,
    provider: OllamaEmbeddingProvider,
    collection_name: str,
    *,
    batch_size: int,
    max_chars: int,
    force: bool,
) -> tuple[int, int]:
    source = database[collection_name]
    target = database[VECTOR_COLLECTION]
    cursor = source.find({}, no_cursor_timeout=True).batch_size(batch_size)
    processed = 0
    written = 0
    pending: list[dict[str, Any]] = []

    async def flush() -> None:
        nonlocal written
        if not pending:
            return
        candidates = pending[:]
        pending.clear()
        ids = [item["vector_id"] for item in candidates]
        present = set() if force else existing_ids(target, ids)
        candidates = [item for item in candidates if item["vector_id"] not in present]
        if not candidates:
            return
        vectors = await provider.embed([item["text"] for item in candidates])
        operations = []
        for item, vector in zip(candidates, vectors, strict=True):
            if len(vector) != VECTOR_DIMENSIONS:
                raise ValueError(f"Unexpected embedding width {len(vector)} for {collection_name}")
            doc = vector_document(collection_name, item["document"], item["text"], vector)
            operations.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
        if operations:
            target.bulk_write(operations, ordered=False)
            written += len(operations)

    try:
        for document in cursor:
            text = source_text(collection_name, document, max_chars)
            if not text:
                processed += 1
                continue
            vector_id = stable_vector_id(collection_name, document.get("_id", ""))
            pending.append({"vector_id": vector_id, "document": document, "text": text})
            processed += 1
            if len(pending) >= batch_size:
                await flush()
                if processed % (batch_size * 10) == 0 or written:
                    print(f"    {collection_name}: scanned={processed:,}, vectors_written={written:,}", flush=True)
        await flush()
    finally:
        cursor.close()
    return processed, written


async def run(args: argparse.Namespace) -> None:
    client = MongoClient(args.uri, serverSelectionTimeoutMS=10_000)
    provider = OllamaEmbeddingProvider(
        model=args.model,
        dimensions=VECTOR_DIMENSIONS,
        base_url=args.ollama_url,
        timeout=args.timeout,
    )
    try:
        client.admin.command("ping")
        database = client[args.db]
        database[VECTOR_COLLECTION].create_index("metadata.source_collection", name="rag_source_collection")
        print(f"MongoDB connected: {args.db}; Ollama model: {args.model}")
        total_scanned = total_written = 0
        for collection_name in args.collections:
            if collection_name not in database.list_collection_names():
                print(f"Skipping missing collection: {collection_name}")
                continue
            print(f"Embedding {collection_name} ...", flush=True)
            scanned, written = await embed_collection(
                database,
                provider,
                collection_name,
                batch_size=args.batch_size,
                max_chars=args.max_chars,
                force=args.force,
            )
            total_scanned += scanned
            total_written += written
            print(f"  {collection_name}: scanned={scanned:,}, vectors_written={written:,}", flush=True)
        print(f"Embedding complete: scanned={total_scanned:,}, vectors_written={total_written:,}, stored={database[VECTOR_COLLECTION].count_documents({}):,}")
    finally:
        await provider.close()
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", DEFAULT_URI))
    parser.add_argument("--db", default=os.getenv("DB_NAME", "careguide"))
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--model", default=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe"))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("OLLAMA_API_TIMEOUT", "300")))
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-chars", type=int, default=12000)
    parser.add_argument("--force", action="store_true", help="Re-embed vectors even when a valid 1536d vector exists")
    parser.add_argument("--collections", nargs="+", default=list(DEFAULT_COLLECTIONS))
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
