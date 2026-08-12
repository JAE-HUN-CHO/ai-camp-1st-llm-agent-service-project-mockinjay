"""Load the repository's CKD source data into the local CareGuide MongoDB.

The source files are intentionally loaded with deterministic string ``_id``
values so this command is safe to re-run.  It does not delete or replace
existing documents; each source record is upserted by its content identity.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, TEXT, MongoClient, UpdateOne
from pymongo.errors import PyMongoError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URI = "mongodb://careguide:careguide_local@127.0.0.1:27017/?authSource=admin&directConnection=true"
BATCH_SIZE = 500


def digest(*values: Any) -> str:
    payload = "\x1f".join(str(value or "").strip() for value in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_id(document: dict[str, Any], prefix: str, *identity: Any) -> dict[str, Any]:
    # JSON exports can contain Mongo Extended JSON _id objects.  Keep the
    # original value under source_id, but use a deterministic BSON-safe id.
    original_id = document.pop("_id", None)
    if original_id is not None:
        document["source_id"] = original_id.get("$oid", original_id) if isinstance(original_id, dict) else original_id
    document["_id"] = f"{prefix}:{digest(*identity)}"
    return document


def jsonl(path: Path, *, skip_invalid: bool = False) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                if skip_invalid:
                    print(f"    skipping invalid JSON at {path.name}:{line_number}: {exc.msg}", flush=True)
                    continue
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if isinstance(value, dict):
                yield value


def upsert_documents(collection, documents: Iterable[dict[str, Any]]) -> int:
    operations: list[UpdateOne] = []
    seen = 0
    for document in documents:
        operations.append(UpdateOne({"_id": document["_id"]}, {"$set": document}, upsert=True))
        seen += 1
        if len(operations) >= BATCH_SIZE:
            collection.bulk_write(operations, ordered=False)
            operations.clear()
            print(f"    processed={seen:,}", flush=True)
    if operations:
        collection.bulk_write(operations, ordered=False)
    return seen


def paper_documents(path: Path) -> Iterator[dict[str, Any]]:
    for document in jsonl(path):
        metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
        identity = metadata.get("pmid") or metadata.get("doi") or document.get("title")
        document = clean_id(document, "paper", identity, document.get("abstract"))
        document["text_hash"] = digest(document.get("title"), document.get("abstract"))
        document["ingest_source"] = path.name
        yield document


def qa_documents(path: Path) -> Iterator[dict[str, Any]]:
    for document in jsonl(path):
        question = document.get("question", "")
        answer = document.get("answer", "")
        document = clean_id(document, "qa", question, answer)
        document["question_hash"] = digest(question)
        document["ingest_source"] = path.name
        yield document


def medical_documents(path: Path) -> Iterator[dict[str, Any]]:
    # This repository export contains one truncated trailing patent record.
    # Keep all valid records and make the known bad line non-blocking.
    for document in jsonl(path, skip_invalid=True):
        text = document.get("text") or document.get("raw_text") or ""
        document = clean_id(document, "medical", document.get("id"), text)
        document["text_hash"] = digest(text)
        document["ingest_source"] = path.name
        yield document


def guideline_documents(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        records = json.load(stream)
    if not isinstance(records, list):
        raise TypeError(f"Expected a JSON list in {path}")
    for document in records:
        if not isinstance(document, dict):
            continue
        text = document.get("text") or document.get("raw_text") or ""
        document = clean_id(document, "guideline", document.get("id"), text)
        document["text_hash"] = digest(text)
        document["ingest_source"] = path.name
        yield document


def food_documents(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            values = [row.get(key, "") for key in row]
            document = dict(row)
            document = clean_id(document, "food", *values)
            document["food_hash"] = digest(*values)
            document["ingest_source"] = path.name
            yield document


def ensure_indexes(db) -> None:
    specs = {
        "papers_kidney": [([('metadata.pmid', ASCENDING)], {"name": "papers_pmid", "sparse": True}), ([('metadata.doi', ASCENDING)], {"name": "papers_doi", "sparse": True}), ([('title', TEXT), ('abstract', TEXT)], {"name": "papers_text"})],
        "medical_kidney": [([('text_hash', ASCENDING)], {"name": "medical_text_hash", "unique": True}), ([('text', TEXT), ('keyword', TEXT)], {"name": "medical_text"})],
        "qa_kidney": [([('question_hash', ASCENDING)], {"name": "qa_question_hash"}), ([('question', TEXT), ('answer', TEXT)], {"name": "qa_text"})],
        "guidelines_kidney": [([('text_hash', ASCENDING)], {"name": "guideline_text_hash", "unique": True}), ([('raw_text', TEXT), ('category', TEXT)], {"name": "guideline_text"})],
        "nutrition_foods": [([('food_hash', ASCENDING)], {"name": "nutrition_food_hash", "unique": True}), ([('식품명', TEXT)], {"name": "nutrition_food_name"})],
    }
    for collection_name, indexes in specs.items():
        for keys, options in indexes:
            try:
                db[collection_name].create_index(keys, **options)
            except PyMongoError as exc:
                # Existing incompatible indexes should be visible, but must
                # not make a repeatable ingestion fail after data is loaded.
                print(f"    index warning {collection_name}.{options['name']}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", DEFAULT_URI))
    parser.add_argument("--db", default=os.getenv("DB_NAME", "careguide"))
    parser.add_argument("--skip-food", action="store_true")
    args = parser.parse_args()

    sources = [
        ("papers_kidney", ROOT / "data/kidney_filtered/papers_kidney.jsonl", paper_documents),
        ("qa_kidney", ROOT / "data/kidney_filtered/qa_kidney.jsonl", qa_documents),
        ("medical_kidney", ROOT / "data/medical_data_enhanced.jsonl", medical_documents),
        ("guidelines_kidney", ROOT / "data/kidney_filtered/guidlines_kidney.json", guideline_documents),
    ]
    if not args.skip_food:
        sources.append(("nutrition_foods", ROOT / "data/nutri/RAG/food_database_cleaned_df.csv", food_documents))

    client = MongoClient(args.uri, serverSelectionTimeoutMS=10_000)
    try:
        client.admin.command("ping")
        db = client[args.db]
        print(f"MongoDB connected: {args.db}")
        for collection_name, path, factory in sources:
            if not path.exists():
                raise FileNotFoundError(path)
            print(f"Loading {collection_name} from {path} ...", flush=True)
            processed = upsert_documents(db[collection_name], factory(path))
            print(f"  processed={processed:,}, stored={db[collection_name].count_documents({}):,}", flush=True)
        ensure_indexes(db)
        print("Structured data load complete")
    finally:
        client.close()


if __name__ == "__main__":
    main()
