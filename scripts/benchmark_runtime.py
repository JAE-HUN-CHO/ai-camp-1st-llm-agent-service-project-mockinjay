"""Measure deterministic HTTP overhead for the chat stream contract.

This benchmark deliberately uses the same FastAPI route with a fake router and
context store.  It measures request/SSE framing/persistence overhead only; it
must not be reported as an LLM or MongoDB provider latency measurement.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api import chat


class _FakeContextManager:
    async def get_user_context(self, _user_id: str) -> dict:
        return {}

    async def save_conversation(
        self,
        _user_id: str,
        _session_id: str,
        _agent_type: str,
        _user_input: str,
        _agent_response: str,
        _room_id: str | None = None,
    ) -> None:
        return None

    async def analyze_and_update_context(self, _user_id: str) -> None:
        return None


class _FakeRouter:
    async def process_stream(self, _request):
        yield {"status": "streaming", "content": "hello ", "agent_type": "test"}
        yield {"status": "complete", "content": "hello world", "agent_type": "test"}


def _client() -> TestClient:
    manager = _FakeContextManager()
    context_system = SimpleNamespace(
        session_manager=SimpleNamespace(get_session=lambda _session_id: None),
        context_engineer=SimpleNamespace(
            db_manager=manager,
            get_user_context=manager.get_user_context,
            analyze_and_update_context=manager.analyze_and_update_context,
        ),
    )
    runtime = SimpleNamespace(router_agent=_FakeRouter())
    app = FastAPI()
    app.state.context_system = context_system
    app.state.agent_runtime = runtime
    app.include_router(chat.router)
    return TestClient(app)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, int((len(ordered) * percentile) + 0.999999))
    return ordered[rank - 1]


def run(iterations: int) -> dict[str, object]:
    if iterations < 2:
        raise ValueError("iterations must be at least 2")
    latencies: list[float] = []
    with _client() as client:
        for index in range(iterations):
            started = time.perf_counter()
            response = client.post(
                "/api/chat/stream",
                json={
                    "query": f"benchmark-{index}",
                    "session_id": f"benchmark-session-{index}",
                    "user_id": "benchmark-user",
                },
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            if response.status_code != 200 or not response.text.endswith("data: [DONE]\n\n"):
                raise RuntimeError(
                    f"chat stream contract failed: {response.status_code} {response.text[:200]}"
                )
            latencies.append(elapsed_ms)

    return {
        "benchmark": "chat_stream_fake_adapter",
        "iterations": iterations,
        "unit": "milliseconds",
        "p50": round(_percentile(latencies, 0.50), 3),
        "p95": round(_percentile(latencies, 0.95), 3),
        "min": round(min(latencies), 3),
        "max": round(max(latencies), 3),
        "scope": "FastAPI route + SSE framing + fake persistence; excludes LLM, network, and MongoDB latency",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.iterations)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
