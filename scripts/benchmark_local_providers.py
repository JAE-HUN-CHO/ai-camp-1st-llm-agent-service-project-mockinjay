"""Measure local Ollama generation and embedding provider latency."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.adapters.ollama.embedding import OllamaEmbeddingProvider


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * fraction + 0.999999))
    return ordered[rank - 1]


async def run(iterations: int, model: str) -> dict[str, object]:
    base_url = "http://127.0.0.1:11434"
    generation: list[float] = []
    embedding: list[float] = []
    async with httpx.AsyncClient(timeout=60) as client:
        for index in range(iterations):
            started = time.perf_counter()
            response = await client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": f"Reply with LOCAL_OK_{index}", "stream": False},
            )
            response.raise_for_status()
            if not response.json().get("response"):
                raise RuntimeError("Ollama generation returned no response")
            generation.append((time.perf_counter() - started) * 1000)

    provider = OllamaEmbeddingProvider()
    try:
        for _ in range(iterations):
            started = time.perf_counter()
            vectors = await provider.embed(["chronic kidney disease diet"])
            if not vectors or len(vectors[0]) != 1536:
                raise RuntimeError("Ollama embedding did not produce 1536 dimensions")
            embedding.append((time.perf_counter() - started) * 1000)
    finally:
        await provider.close()

    return {
        "benchmark": "ollama_local_providers",
        "iterations": iterations,
        "generation_model": model,
        "embedding_model": provider.model,
        "unit": "milliseconds",
        "generation_p50": round(percentile(generation, 0.50), 3),
        "generation_p95": round(percentile(generation, 0.95), 3),
        "embedding_p50": round(percentile(embedding, 0.50), 3),
        "embedding_p95": round(percentile(embedding, 0.95), 3),
        "embedding_dimensions": 1536,
        "scope": "local Ollama HTTP provider including lossless 768d-to-1536d expansion",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--model", default="qwen3.6:27b-mlx")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(asyncio.run(run(args.iterations, args.model)), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
