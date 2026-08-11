"""Measure indexed room/history queries against a local Atlas Local fixture."""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path

from pymongo import ASCENDING, DESCENDING, MongoClient


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * fraction + 0.999999))
    return ordered[rank - 1]


def run(iterations: int) -> dict[str, object]:
    uri = os.getenv(
        "MONGODB_URI",
        "mongodb://careguide:careguide_local@127.0.0.1:27017/?authSource=admin&directConnection=true",
    )
    database_name = os.getenv("DB_NAME", "careguide")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    collection_name = f"_careguide_perf_{uuid.uuid4().hex}"
    try:
        client.admin.command("ping")
        db = client[database_name]
        rooms = db[collection_name]
        history = db[f"{collection_name}_history"]
        rooms.create_index(
            [("user_id", ASCENDING), ("is_deleted", ASCENDING), ("last_activity", DESCENDING)],
            name="perf_rooms_user_deleted_activity",
        )
        history.create_index(
            [("room_id", ASCENDING), ("timestamp", DESCENDING)],
            name="perf_history_room_timestamp",
        )
        user_id = f"perf-{uuid.uuid4().hex}"
        room_documents = [
            {"room_id": f"{user_id}-{index}", "user_id": user_id, "is_deleted": False, "last_activity": index}
            for index in range(100)
        ]
        rooms.insert_many(room_documents)
        history.insert_many(
            {
                "room_id": room["room_id"],
                "timestamp": timestamp,
                "user_id": user_id,
            }
            for room in room_documents
            for timestamp in range(5)
        )

        room_latencies: list[float] = []
        history_latencies: list[float] = []
        for _ in range(iterations):
            started = time.perf_counter()
            list(rooms.find({"user_id": user_id, "is_deleted": False}).sort("last_activity", DESCENDING).limit(50))
            room_latencies.append((time.perf_counter() - started) * 1000)

            started = time.perf_counter()
            list(history.find({"room_id": room_documents[0]["room_id"]}).sort("timestamp", DESCENDING).limit(50))
            history_latencies.append((time.perf_counter() - started) * 1000)
    finally:
        if "db" in locals():
            db[collection_name].drop()
            db[f"{collection_name}_history"].drop()
        client.close()

    return {
        "benchmark": "mongodb_indexed_room_history",
        "iterations": iterations,
        "fixture": {"rooms": 100, "history_per_room": 5},
        "unit": "milliseconds",
        "rooms_p50": round(percentile(room_latencies, 0.50), 3),
        "rooms_p95": round(percentile(room_latencies, 0.95), 3),
        "history_p50": round(percentile(history_latencies, 0.50), 3),
        "history_p95": round(percentile(history_latencies, 0.95), 3),
        "scope": "synthetic local Atlas Local fixture with compound indexes; excludes application serialization",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(run(args.iterations), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
