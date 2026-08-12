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


async def run() -> None:
    print("connecting", flush=True)
    await Database.connect()
    print("connected", flush=True)
    service = OllamaChatService(database=Database.db, top_k=1)
    smoke_id = f"careguide-smoke-{uuid.uuid4()}"
    collection = Database.db[service.collection_name]
    try:
        vector = await service._embed("만성콩팥병 혈압 관리")
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
        # Atlas Local updates vector search indexes asynchronously.
        await asyncio.sleep(5)
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
        assert len(vector) == 1536
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
