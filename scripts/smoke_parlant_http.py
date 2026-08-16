#!/usr/bin/env python3
"""Strict local Parlant customer → session → message HTTP smoke."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
import time

import httpx

from smoke_common import default_artifact_dir, digest_text, require_local_http, utc_now, write_json
from verification_manifest import append_command


TARGETS = (
    ("research", "CareGuide_v2", "만성 신장질환 공개 연구 근거의 출처를 알려주세요."),
    ("welfare", "MedicalWelfare_Agent", "만성 신장질환 관련 공개 복지 제도의 출처를 알려주세요."),
)


def _items(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


async def _json(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> tuple[int, object]:
    response = await client.request(method, url, **kwargs)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"{method} {url} did not return JSON ({response.status_code})") from exc
    return response.status_code, payload


async def _discover(client: httpx.AsyncClient, base_url: str, expected_name: str) -> tuple[str, dict]:
    health = await client.get(f"{base_url}/healthz")
    if health.status_code != 200:
        raise RuntimeError(f"readiness failed: /healthz returned HTTP {health.status_code}")
    try:
        health_payload = health.json()
    except ValueError as exc:
        raise RuntimeError("readiness failed: /healthz did not return JSON") from exc
    if not isinstance(health_payload, dict):
        raise RuntimeError("readiness failed: /healthz JSON was not an object")

    for prefix in ("", "/api"):
        response = await client.get(f"{base_url}{prefix}/agents")
        if response.status_code != 200:
            continue
        try:
            payload = response.json()
        except ValueError:
            continue
        for agent in _items(payload):
            if agent.get("name") == expected_name and isinstance(agent.get("id"), str):
                return prefix, agent
    raise RuntimeError("readiness failed: no 200 JSON target agent identity")


def _event_summary(event: dict) -> dict:
    data = event.get("data")
    if isinstance(data, dict):
        text = data.get("message") or data.get("content") or ""
    else:
        text = data if isinstance(data, str) else ""
    return {
        "id": event.get("id"),
        "offset": event.get("offset"),
        "kind": event.get("kind"),
        "source": event.get("source"),
        "status": event.get("status"),
        "content": digest_text(text) if text else None,
    }


async def smoke_target(
    *, name: str, base_url: str, expected_agent: str, prompt: str, timeout: float
) -> dict:
    started = utc_now()
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(timeout=httpx.Timeout(min(timeout, 20.0))) as client:
        prefix, agent = await _discover(client, base_url, expected_agent)
        endpoint = f"{base_url}{prefix}"
        run_key = str(int(time.time() * 1000))
        status, customer = await _json(
            client,
            "POST",
            f"{endpoint}/customers",
            json={"name": f"careguide-smoke-{name}-{run_key}", "metadata": {"purpose": "local-verification"}},
        )
        if not 200 <= status < 300 or not isinstance(customer, dict) or not customer.get("id"):
            raise RuntimeError("customer creation failed schema/status validation")
        status, session = await _json(
            client,
            "POST",
            f"{endpoint}/sessions",
            params={"allow_greeting": "false"},
            json={"agent_id": agent["id"], "customer_id": customer["id"], "title": "CareGuide local smoke"},
        )
        if not 200 <= status < 300 or not isinstance(session, dict) or not session.get("id"):
            raise RuntimeError("session creation failed schema/status validation")
        status, customer_event = await _json(
            client,
            "POST",
            f"{endpoint}/sessions/{session['id']}/events",
            json={"kind": "message", "source": "customer", "message": prompt},
        )
        if not 200 <= status < 300 or not isinstance(customer_event, dict) or not customer_event.get("id"):
            raise RuntimeError("customer event creation failed schema/status validation")

        response_events: list[dict] = []
        while time.monotonic() < deadline:
            remaining = max(1, min(5, int(deadline - time.monotonic())))
            response = await client.get(
                f"{endpoint}/sessions/{session['id']}/events",
                params={"min_offset": int(customer_event.get("offset", 0)) + 1, "wait_for_data": remaining},
            )
            if response.status_code == 504:
                continue
            if response.status_code != 200:
                raise RuntimeError(f"event poll returned HTTP {response.status_code}")
            try:
                events = _items(response.json())
            except ValueError as exc:
                raise RuntimeError("event poll did not return JSON") from exc
            response_events = [
                event
                for event in events
                if event.get("kind") == "message" and event.get("source") != "customer" and event.get("id")
            ]
            if response_events:
                break
        if not response_events:
            raise TimeoutError("no agent message event before smoke timeout")

        return {
            "schema_version": 1,
            "ready": True,
            "flow_complete": True,
            "target": name,
            "provider": "parlant-local",
            "endpoint": endpoint,
            "agent": {"id": agent["id"], "name": agent["name"]},
            "customer_id": customer["id"],
            "session_id": session["id"],
            "customer_event_id": customer_event["id"],
            "response_events": [_event_summary(event) for event in response_events],
            "request_content": digest_text(prompt),
            "started_at": started,
            "finished_at": utc_now(),
        }


async def run(args) -> int:
    artifact_dir = args.artifact_dir or default_artifact_dir()
    urls = {"research": require_local_http(args.research_url), "welfare": require_local_http(args.welfare_url)}
    if urls["research"] == urls["welfare"]:
        raise ValueError("research and welfare endpoints must be distinct")
    targets = TARGETS if args.target == "all" else tuple(t for t in TARGETS if t[0] == args.target)
    exit_code = 0
    for name, expected, prompt in targets:
        try:
            result = await smoke_target(
                name=name,
                base_url=urls[name],
                expected_agent=expected,
                prompt=prompt,
                timeout=args.timeout,
            )
        except BaseException as exc:
            result = exc
        path = artifact_dir / "http" / f"{name}.json"
        if isinstance(result, BaseException):
            exit_code = 1
            write_json(
                path,
                {
                    "schema_version": 1,
                    "ready": False,
                    "flow_complete": False,
                    "target": name,
                    "expected_agent": expected,
                    "provider": "parlant-local",
                    "error_type": type(result).__name__,
                    "error": str(result),
                    "finished_at": utc_now(),
                },
            )
        else:
            write_json(path, result)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-url", default="http://127.0.0.1:8800")
    parser.add_argument("--welfare-url", default="http://127.0.0.1:8801")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--target", choices=("all", "research", "welfare"), default="all")
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    artifact_dir = args.artifact_dir or default_artifact_dir()
    args.artifact_dir = artifact_dir
    started = utc_now()
    try:
        exit_code = asyncio.run(run(args))
    except Exception as exc:
        exit_code = 1
        write_json(
            artifact_dir / "http" / "parlant-smoke-error.json",
            {"error_type": type(exc).__name__, "error": str(exc), "finished_at": utc_now()},
        )
    target_names = ("research", "welfare") if args.target == "all" else (args.target,)
    append_command(
        artifact_dir,
        argv=[sys.executable, *sys.argv],
        exit_code=exit_code,
        started_at=started,
        finished_at=utc_now(),
        artifacts=[f"http/{name}.json" for name in target_names],
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
