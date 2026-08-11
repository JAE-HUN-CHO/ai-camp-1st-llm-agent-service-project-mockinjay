"""Run an opt-in Ollama embedding smoke against the ADR-005 vector width."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.adapters.ollama.embedding import OllamaEmbeddingProvider


async def run(model: str, dimensions: int) -> dict[str, object]:
    provider = OllamaEmbeddingProvider(model=model, dimensions=dimensions)
    try:
        vectors = await provider.embed(["chronic kidney disease diet"])
    finally:
        await provider.close()
    return {
        "provider": "ollama",
        "model": model,
        "target_dimensions": dimensions,
        "actual_dimensions": len(vectors[0]) if vectors else 0,
        "vectors": len(vectors),
        "status": "PASS" if vectors and len(vectors[0]) == dimensions else "FAIL",
        "dimension_policy": "lossless_duplicate_when_source_width_is_half_target",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="nomic-embed-text-v2-moe")
    parser.add_argument("--dimensions", type=int, default=1536)
    args = parser.parse_args()
    result = asyncio.run(run(args.model, args.dimensions))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
