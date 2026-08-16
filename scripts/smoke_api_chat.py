#!/usr/bin/env python3
"""Strict authenticated JSON + SSE smoke for the local FastAPI chat facade."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import uuid

import httpx
from jose import jwt

from smoke_common import default_artifact_dir, digest_text, ensure_redacted, require_local_http, utc_now, write_json
from verification_manifest import append_command


PROMPT = "만성 신장질환의 일반적인 식이 관리 원칙을 근거 중심으로 알려주세요."


class SmokeContractError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        content_type: str | None = None,
    ) -> None:
        """계약 위반 오류를 생성하고 관련 HTTP 응답 메타데이터를 저장합니다.
        
        Parameters:
        	message (str): 오류 메시지
        	status_code (int | None): 관련 HTTP 상태 코드
        	content_type (str | None): 관련 응답의 콘텐츠 유형
        """
        super().__init__(message)
        self.status_code = status_code
        self.content_type = content_type


def parse_sse_line(line: str) -> tuple[str, dict | None]:
    """
    SSE 데이터 라인을 분류하고 JSON 프레임을 파싱합니다.
    
    Parameters:
    	line (str): 파싱할 SSE 데이터 라인
    
    Returns:
    	tuple[str, dict | None]: 라인 분류와 파싱된 JSON 객체를 반환합니다. 분류는 `"ignored"`, `"done"`, `"frame"` 중 하나이며, JSON 프레임이 아닌 경우 데이터는 `None`입니다.
    
    Raises:
    	ValueError: SSE 데이터가 JSON 객체가 아닌 경우 발생합니다.
    """
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
    """
    로컬 인증 채팅 서비스의 일반 및 스트리밍 응답 계약을 검증하고 결과 아티팩트를 저장합니다.
    
    Parameters:
    	args: 기본 URL, 요청 시간 초과, 테스트 시나리오, 아티팩트 저장 경로를 포함하는 실행 인자입니다.
    
    Returns:
    	int: 모든 계약 검증이 성공하면 0을 반환합니다.
    """
    token = os.getenv("CAREGUIDE_SMOKE_TOKEN")
    if not token:
        raise RuntimeError("CAREGUIDE_SMOKE_TOKEN is required and must not be passed on argv")
    base_url = require_local_http(args.base_url)
    headers = {"Authorization": f"Bearer {token}"}
    claims = jwt.get_unverified_claims(token)
    user_id = claims.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        raise RuntimeError("CAREGUIDE_SMOKE_TOKEN must contain a user_id claim")
    artifact_dir = args.artifact_dir
    started = utc_now()
    async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout)) as client:
        room_response = await client.post(
            f"{base_url}/api/rooms",
            headers=headers,
            json={"user_id": user_id, "room_name": "Phase 2 verification"},
        )
        try:
            room_payload = room_response.json()
            room_id = room_payload["data"]["room_id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SmokeContractError(
                "chat room creation failed schema/status validation",
                status_code=room_response.status_code,
                content_type=room_response.headers.get("content-type"),
            ) from exc
        if room_response.status_code != 201 or not isinstance(room_id, str):
            raise SmokeContractError(
                "chat room creation failed schema/status validation",
                status_code=room_response.status_code,
                content_type=room_response.headers.get("content-type"),
            )
        message_id = str(uuid.uuid4())
        response = await client.post(
            f"{base_url}/api/chat/message",
            headers=headers,
            json={
                "query": PROMPT,
                "session_id": room_id,
                "room_id": room_id,
                "client_message_id": message_id,
                "user_profile": "patient",
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise SmokeContractError(
                "chat message returned non-JSON",
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
            ) from exc
        expected_failure_status = {"provider-failure": 503, "timeout": 504}.get(
            args.scenario
        )
        if expected_failure_status is not None:
            if response.status_code != expected_failure_status:
                raise SmokeContractError(
                    "chat message returned unexpected failure status",
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type"),
                )
            failure_frames = []
            failure_done = False
            failure_error = False
            failure_success = False
            async with client.stream(
                "POST",
                f"{base_url}/api/chat/stream",
                headers=headers,
                json={
                    "query": PROMPT,
                    "session_id": room_id,
                    "room_id": room_id,
                    "client_message_id": str(uuid.uuid4()),
                    "user_profile": "patient",
                },
            ) as failure_stream:
                if (
                    failure_stream.status_code != 200
                    or "text/event-stream"
                    not in failure_stream.headers.get("content-type", "")
                ):
                    raise SmokeContractError(
                        "chat stream did not preserve post-header error contract",
                        status_code=failure_stream.status_code,
                        content_type=failure_stream.headers.get("content-type"),
                    )
                async for line in failure_stream.aiter_lines():
                    kind, frame = parse_sse_line(line)
                    if kind == "done":
                        failure_done = True
                        continue
                    if kind != "frame" or frame is None:
                        continue
                    status = frame.get("status")
                    failure_error = failure_error or status == "error" or bool(
                        frame.get("error")
                    )
                    failure_success = failure_success or status in {
                        "complete",
                        "success",
                    }
                    failure_frames.append(
                        {
                            "status": status,
                            "error": digest_text(str(frame.get("error")))
                            if frame.get("error")
                            else None,
                        }
                    )
            if not failure_error or not failure_done or failure_success:
                raise SmokeContractError(
                    "chat stream failure terminal semantics mismatch",
                    status_code=failure_stream.status_code,
                    content_type=failure_stream.headers.get("content-type"),
                )
            failure_frames.insert(
                0,
                {
                    "contract": "post_header_terminal_error",
                    "status_code": failure_stream.status_code,
                    "content_type": failure_stream.headers.get("content-type"),
                    "provider_identity": "ollama",
                },
            )
            failure_path = (
                artifact_dir / "http" / f"chat-{args.scenario}-stream.ndjson"
            )
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            failure_path.write_text(
                serialize_stream_evidence(failure_frames), encoding="utf-8"
            )
            raise SmokeContractError(
                "expected local provider failure observed",
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
            )
        if response.status_code != 200 or payload.get("status") != "success":
            raise SmokeContractError(
                "chat message failed schema/status validation",
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
            )
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
                "room_id": digest_text(room_id),
                "session_id": digest_text(room_id),
                "message_id": digest_text(message_id),
                "message_id_source": "client_message_id",
                "started_at": started,
                "finished_at": utc_now(),
            },
        )

        frames = []
        terminal = None
        done_seen = False
        stream_message_id = str(uuid.uuid4())
        async with client.stream(
            "POST",
            f"{base_url}/api/chat/stream",
            headers=headers,
            json={
                "query": PROMPT,
                "session_id": room_id,
                "room_id": room_id,
                "client_message_id": stream_message_id,
                "user_profile": "patient",
            },
        ) as stream:
            if stream.status_code != 200 or "text/event-stream" not in stream.headers.get("content-type", ""):
                raise SmokeContractError(
                    "chat stream failed HTTP/content-type validation",
                    status_code=stream.status_code,
                    content_type=stream.headers.get("content-type"),
                )
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
                }
                if content:
                    if status in {"complete", "success"}:
                        summary["content"] = digest_text(str(content))
                    else:
                        summary["content_bytes"] = len(str(content).encode("utf-8"))
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
        frames.insert(
            0,
            {
                "contract": "chat_stream_identifiers",
                "room_id": digest_text(room_id),
                "session_id": digest_text(room_id),
                "message_id": digest_text(stream_message_id),
                "message_id_source": "client_message_id",
                "provider_identity": "ollama",
                "content_type": stream.headers.get("content-type"),
                "status_code": stream.status_code,
            },
        )
        ndjson_path = artifact_dir / "http" / "chat-stream.ndjson"
        ndjson_path.parent.mkdir(parents=True, exist_ok=True)
        ndjson_path.write_text(serialize_stream_evidence(frames), encoding="utf-8")
    return 0


def main() -> int:
    """
    명령줄 인자를 해석하고 채팅 API 스모크 테스트를 실행한 뒤 결과를 아티팩트로 기록합니다.
    
    Returns:
    	int: 스모크 테스트의 종료 상태 코드
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--scenario",
        choices=("success", "provider-failure", "timeout"),
        default="success",
    )
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir or default_artifact_dir()
    args.artifact_dir = artifact_dir
    started = utc_now()
    candidates = (
        ["http/chat-message.json", "http/chat-stream.ndjson"]
        if args.scenario == "success"
        else []
    )
    try:
        exit_code = asyncio.run(run(args))
    except Exception as exc:
        exit_code = 1
        error_name = f"http/chat-{args.scenario}-error.json"
        error_payload = {
            "error_type": type(exc).__name__,
            "error_message": digest_text(str(exc)),
            "finished_at": utc_now(),
        }
        if isinstance(exc, SmokeContractError):
            error_payload.update(
                {
                    "status_code": exc.status_code,
                    "content_type": exc.content_type,
                }
            )
        write_json(artifact_dir / error_name, error_payload)
        candidates.extend(
            [
                error_name,
                f"http/chat-{args.scenario}-stream.ndjson",
            ]
        )
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
