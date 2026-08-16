#!/usr/bin/env python3
"""Strict authenticated JSON + SSE smoke for the local FastAPI chat facade."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

import httpx

from smoke_common import default_artifact_dir, digest_text, ensure_redacted, require_local_http, utc_now, write_json
from verification_manifest import append_command


PROMPT = "만성 신장질환의 일반적인 식이 관리 원칙을 근거 중심으로 알려주세요."


def parse_sse_line(line: str) -> tuple[str, dict | None]:
    if not line.startswith("data:"):
        return "ignored", None
    data = line[5:].removeprefix(" ")
    if data == "[DONE]":
        return "done", None
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("SSE data must be a JSON object")
    return "frame", payload


def serialize_stream_evidence(frames: list[dict]) -> str:
    """Serialize one JSON object per line, keeping transport completion distinct."""
    records = [*frames, {"transport_done": True}]
    return "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"


async def run(args) -> int:
    token = os.getenv("CAREGUIDE_SMOKE_TOKEN")
    if not token:
        raise RuntimeError("CAREGUIDE_SMOKE_TOKEN is required and must not be passed on argv")
    base_url = require_local_http(args.base_url)
    headers = {"Authorization": f"Bearer {token}"}
    artifact_dir = args.artifact_dir
    started = utc_now()
    async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout)) as client:
        response = await client.post(
            f"{base_url}/api/chat/message",
            headers=headers,
            json={"query": PROMPT, "session_id": "default", "user_profile": "patient"},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"chat message returned non-JSON HTTP {response.status_code}") from exc
        if response.status_code != 200 or payload.get("status") != "success":
            raise RuntimeError(f"chat message failed schema/status validation ({response.status_code})")
        answer = payload.get("content") or payload.get("answer") or ""
        provider = (payload.get("metadata") or {}).get("provider")
        identity = payload.get("agent_type") or "ollama_rag"
        if not answer or provider != "ollama" or identity != "ollama_rag":
            raise RuntimeError("chat message provider/agent identity validation failed")
        write_json(
            artifact_dir / "http" / "chat-message.json",
            {
                "schema_version": 1,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "provider": provider,
                "agent_identity": identity,
                "request_content": digest_text(PROMPT),
                "response_content": digest_text(str(answer)),
                "started_at": started,
                "finished_at": utc_now(),
            },
        )

        frames = []
        terminal = None
        done_seen = False
        async with client.stream(
            "POST",
            f"{base_url}/api/chat/stream",
            headers=headers,
            json={"query": PROMPT, "session_id": "default", "user_profile": "patient"},
        ) as stream:
            if stream.status_code != 200 or "text/event-stream" not in stream.headers.get("content-type", ""):
                raise RuntimeError(f"chat stream failed HTTP/content-type validation ({stream.status_code})")
            async for line in stream.aiter_lines():
                kind, frame = parse_sse_line(line)
                if kind == "done":
                    done_seen = True
                    continue
                if kind != "frame" or frame is None:
                    continue
                status = frame.get("status")
                content = frame.get("content") or frame.get("answer") or ""
                summary = {
                    "index": len(frames),
                    "status": status,
                    "agent_identity": frame.get("agent_type"),
                    "content": digest_text(str(content)) if content else None,
                }
                ensure_redacted(summary)
                frames.append(summary)
                if status in {"complete", "success"}:
                    terminal = summary
                if status == "error" or frame.get("error"):
                    raise RuntimeError("chat stream emitted terminal error")
        if terminal is None or not done_seen:
            raise RuntimeError("chat stream requires terminal success frame and separate [DONE]")
        if terminal.get("agent_identity") not in {None, "ollama_rag"}:
            raise RuntimeError("chat stream agent identity mismatch")
        ndjson_path = artifact_dir / "http" / "chat-stream.ndjson"
        ndjson_path.parent.mkdir(parents=True, exist_ok=True)
        ndjson_path.write_text(serialize_stream_evidence(frames), encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir or default_artifact_dir()
    args.artifact_dir = artifact_dir
    started = utc_now()
    candidates = ["http/chat-message.json", "http/chat-stream.ndjson"]
    try:
        exit_code = asyncio.run(run(args))
    except Exception as exc:
        exit_code = 1
        write_json(
            artifact_dir / "http" / "chat-smoke-error.json",
            {
                "error_type": type(exc).__name__,
                "error_message": digest_text(str(exc)),
                "finished_at": utc_now(),
            },
        )
        candidates.append("http/chat-smoke-error.json")
    artifacts = [name for name in candidates if (artifact_dir / name).is_file()]
    append_command(
        artifact_dir,
        argv=[sys.executable, *sys.argv],
        exit_code=exit_code,
        started_at=started,
        finished_at=utc_now(),
        artifacts=artifacts,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
