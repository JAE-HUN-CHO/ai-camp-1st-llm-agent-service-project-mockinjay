"""Exercise the real Ollama + MongoDB vector-grounded chat path.

The smoke inserts one clearly named temporary vector document so an empty
development database still verifies retrieval, then removes that document.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.connection import Database
from app.services.ollama_chat import OllamaChatService
from pymongo.errors import OperationFailure


def _is_transient_index_error(error: OperationFailure) -> bool:
    message = str(error).lower()
    if any(token in message for token in ("authentication", "not authorized", "unauthorized", "connection")):
        return False
    return any(token in message for token in ("index", "vectorsearch", "vector search", "not ready"))


async def run() -> None:
    print("connecting", flush=True)
    await Database.connect()
    print("connected", flush=True)
    service = OllamaChatService(database=Database.db, top_k=1)
    smoke_id = f"careguide-smoke-{uuid.uuid4()}"
    collection = Database.db[service.collection_name]
    try:
        vector = await service.embed_query("만성콩팥병 혈압 관리")
        print("embedded", len(vector), flush=True)
        await collection.insert_one(
            {
                "_id": smoke_id,
                "embedding": vector,
                "title": "CareGuide smoke evidence",
                "text": "만성콩팥병 환자는 혈압과 단백뇨를 정기적으로 확인해야 합니다.",
                "source": "temporary-smoke-fixture",
            }
        )
        print("inserted", flush=True)
        # Atlas Local updates vector search indexes asynchronously. Poll with a
        # bounded timeout instead of assuming a fixed indexing delay.
        deadline = asyncio.get_running_loop().time() + 30
        while True:
            try:
                retrieved = await service.retrieve(vector)
            except OperationFailure as exc:
                if not _is_transient_index_error(exc):
                    raise
                retrieved = []
            if any(item.get("_id") == smoke_id for item in retrieved):
                break
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("Timed out waiting for the smoke vector to become searchable")
            await asyncio.sleep(1)
        result = await service.generate("만성콩팥병 혈압 관리", profile="patient")
        print("generated", bool(result.get("answer")), flush=True)
        events = [
            event
            async for event in service.stream("만성콩팥병 혈압 관리", profile="patient")
        ]
        print("streamed", len(events), flush=True)
        streamed = "".join(
            event.get("content", "")
            for event in events
            if event.get("status") == "streaming"
        )
        assert len(vector) == service.dimensions
        assert result["metadata"]["retrieved_count"] >= 1
        assert result["answer"]
        assert streamed
        print(
            {
                "embedding_dimensions": len(vector),
                "retrieved_count": result["metadata"]["retrieved_count"],
                "generated": bool(result["answer"]),
                "streamed": bool(streamed),
                "status": "PASS",
            }
        )
    finally:
        await collection.delete_one({"_id": smoke_id})
        await service.close()
        await Database.disconnect()


if __name__ == "__main__":
    asyncio.run(run())
