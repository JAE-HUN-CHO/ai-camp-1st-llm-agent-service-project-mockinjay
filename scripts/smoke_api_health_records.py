#!/usr/bin/env python3
"""Authenticated local HTTP smoke for the frozen Health Records REST v1 API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import httpx
from jose import jwt

from smoke_common import (
    default_artifact_dir,
    digest_text,
    require_local_http,
    utc_now,
    write_json,
)
from verification_manifest import append_command


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "tests/backend/fixtures/health-records-v1-contract.json").read_text(
        encoding="utf-8"
    )
)
RECORD_KEYS = set(CONTRACT["record_keys"])


class SmokeContractError(RuntimeError):
    """Report only contract metadata, never a response body."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        content_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.content_type = content_type


def _json(response: httpx.Response, expected_status: int) -> object:
    content_type = response.headers.get("content-type", "")
    if response.status_code != expected_status or "application/json" not in content_type:
        raise SmokeContractError(
            "Health Records status or media type mismatch",
            status_code=response.status_code,
            content_type=content_type,
        )
    try:
        return response.json()
    except ValueError as exc:
        raise SmokeContractError(
            "Health Records response was not JSON",
            status_code=response.status_code,
            content_type=content_type,
        ) from exc


def _record(response: httpx.Response) -> dict[str, object]:
    payload = _json(response, 200)
    if not isinstance(payload, dict) or set(payload) != RECORD_KEYS:
        raise SmokeContractError(
            "Health Records response keys changed",
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
        )
    return payload


def _error(response: httpx.Response, contract_name: str) -> dict[str, object]:
    expected = CONTRACT["errors"][contract_name]
    payload = _json(response, int(expected["status"]))
    if payload != {"detail": expected["detail"]}:
        raise SmokeContractError(
            "Health Records error payload changed",
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
        )
    return payload


def _summary(response: httpx.Response, payload: object) -> dict[str, object]:
    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "body": digest_text(json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    }


def run(args: argparse.Namespace) -> int:
    token = os.getenv("CAREGUIDE_SMOKE_TOKEN")
    other_token = os.getenv("CAREGUIDE_OTHER_SMOKE_TOKEN")
    health_canary = os.getenv("CAREGUIDE_HEALTH_CANARY")
    if not token or not other_token or not health_canary:
        raise RuntimeError("Health Records smoke environment is incomplete")

    claims = jwt.get_unverified_claims(token)
    owner_id = claims.get("user_id")
    if not isinstance(owner_id, str) or not owner_id:
        raise RuntimeError("Health Records smoke owner claim is missing")

    base_url = require_local_http(args.base_url)
    owner_headers = {"Authorization": f"Bearer {token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    started_at = utc_now()
    operations: dict[str, object] = {}
    record_ids: list[str] = []
    owner_binding = False
    cross_user_cases_passed = 0
    unauthorized_write_count = 1
    null_clear_preserved = False
    unset_fields_preserved = False
    list_order_preserved = False
    error_contract_checks = 0

    with httpx.Client(timeout=args.timeout) as client:
        try:
            created_records: list[tuple[httpx.Response, dict[str, object]]] = []
            for date, gfr, memo in (
                ("2099-01-02", 61.0, health_canary),
                ("2099-01-01", 60.0, None),
            ):
                response = client.post(
                    f"{base_url}/api/health-records/",
                    headers=owner_headers,
                    json={
                        "date": date,
                        "hospital": "Synthetic Verification Clinic",
                        "creatinine": 1.23,
                        "gfr": gfr,
                        "memo": memo,
                    },
                )
                created_record = _record(response)
                created_id = created_record.get("id")
                if not isinstance(created_id, str) or created_record.get("user_id") != owner_id:
                    raise SmokeContractError("Health Records owner or ID binding failed")
                record_ids.append(created_id)
                created_records.append((response, created_record))
            owner_binding = len(record_ids) == 2

            created_response, created = created_records[0]
            record_id = record_ids[0]
            operations["create"] = _summary(created_response, created)
            operations["create_order_probe"] = _summary(*created_records[1])

            listed_response = client.get(
                f"{base_url}/api/health-records/", headers=owner_headers
            )
            listed = _json(listed_response, 200)
            if not isinstance(listed, list):
                raise SmokeContractError("Health Records list schema changed")
            matching = [
                item
                for item in listed
                if isinstance(item, dict) and item.get("id") in set(record_ids)
            ]
            if [item.get("id") for item in matching] != record_ids:
                raise SmokeContractError("Health Records date-descending order changed")
            list_order_preserved = True
            operations["list"] = {
                **_summary(listed_response, matching),
                "matching_record_count": len(matching),
            }

            empty_response = client.put(
                f"{base_url}/api/health-records/{record_id}",
                headers=owner_headers,
                json={},
            )
            empty_payload = _error(empty_response, "empty_update")
            error_contract_checks += 1
            operations["empty_update"] = _summary(empty_response, empty_payload)

            denied_update_response = client.put(
                f"{base_url}/api/health-records/{record_id}",
                headers=other_headers,
                json={"memo": None},
            )
            denied_update = _error(denied_update_response, "invalid_or_unowned_id")
            error_contract_checks += 1
            cross_user_cases_passed += 1
            operations["cross_user_update"] = _summary(
                denied_update_response, denied_update
            )

            denied_delete_response = client.delete(
                f"{base_url}/api/health-records/{record_id}", headers=other_headers
            )
            denied_delete = _error(denied_delete_response, "invalid_or_unowned_id")
            error_contract_checks += 1
            cross_user_cases_passed += 1
            operations["cross_user_delete"] = _summary(
                denied_delete_response, denied_delete
            )

            owner_after_denial_response = client.get(
                f"{base_url}/api/health-records/", headers=owner_headers
            )
            owner_after_denial = _json(owner_after_denial_response, 200)
            if not isinstance(owner_after_denial, list):
                raise SmokeContractError("Health Records list schema changed")
            unchanged = [
                item
                for item in owner_after_denial
                if isinstance(item, dict) and item.get("id") == record_id
            ]
            if unchanged != [created]:
                raise SmokeContractError("Cross-user request changed the owner record")
            unauthorized_write_count = 0

            updated_response = client.put(
                f"{base_url}/api/health-records/{record_id}",
                headers=owner_headers,
                json={"memo": None},
            )
            updated = _record(updated_response)
            if updated.get("memo") is not None or updated.get("date") != created.get("date"):
                raise SmokeContractError("Health Records null or unset semantics changed")
            null_clear_preserved = True
            unset_fields_preserved = True
            operations["update"] = _summary(updated_response, updated)

            deleted_response = client.delete(
                f"{base_url}/api/health-records/{record_id}", headers=owner_headers
            )
            deleted = _json(deleted_response, 200)
            if deleted != CONTRACT["delete_payload"]:
                raise SmokeContractError("Health Records delete payload changed")
            operations["delete"] = _summary(deleted_response, deleted)

            retry_response = client.delete(
                f"{base_url}/api/health-records/{record_id}", headers=owner_headers
            )
            retry = _error(retry_response, "invalid_or_unowned_id")
            error_contract_checks += 1
            operations["delete_retry"] = _summary(retry_response, retry)

            invalid_response = client.put(
                f"{base_url}/api/health-records/not-an-object-id",
                headers=owner_headers,
                json={"memo": None},
            )
            invalid = _error(invalid_response, "invalid_or_unowned_id")
            error_contract_checks += 1
            operations["invalid_id"] = _summary(invalid_response, invalid)
        finally:
            for synthetic_id in record_ids:
                try:
                    client.delete(
                        f"{base_url}/api/health-records/{synthetic_id}",
                        headers=owner_headers,
                    )
                except httpx.HTTPError:
                    pass

        cleanup_response = client.get(
            f"{base_url}/api/health-records/", headers=owner_headers
        )
        cleanup_records = _json(cleanup_response, 200)
        if not isinstance(cleanup_records, list):
            raise SmokeContractError("Health Records cleanup list schema changed")
        synthetic_leak_count = sum(
            isinstance(item, dict) and item.get("id") in set(record_ids)
            for item in cleanup_records
        )
        if synthetic_leak_count:
            raise SmokeContractError("Health Records synthetic cleanup failed")

    write_json(
        args.artifact_dir / args.artifact_name,
        {
            "schema_version": 1,
            "result": "pass",
            "implementation": args.implementation,
            "record_id": digest_text(record_id),
            "owner_binding": owner_binding,
            "record_keys": sorted(RECORD_KEYS),
            "cross_user_cases": {"passed": cross_user_cases_passed, "total": 2},
            "unauthorized_write_count": unauthorized_write_count,
            "synthetic_leak_count": synthetic_leak_count,
            "null_clear_preserved": null_clear_preserved,
            "unset_fields_preserved": unset_fields_preserved,
            "list_order_preserved": list_order_preserved,
            "error_contract_preserved": error_contract_checks == 5,
            "operations": operations,
            "started_at": started_at,
            "finished_at": utc_now(),
        },
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--implementation", choices=("legacy", "hex"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--artifact-name", type=Path, required=True)
    args = parser.parse_args()
    args.artifact_dir = args.artifact_dir or default_artifact_dir()
    started_at = utc_now()
    exit_code = 0
    artifacts: list[str] = []
    try:
        exit_code = run(args)
        artifacts.append(str(args.artifact_name))
    except Exception as exc:
        exit_code = 1
        error_name = args.artifact_name.with_name(f"{args.artifact_name.stem}-error.json")
        payload: dict[str, object] = {
            "error_type": type(exc).__name__,
            "error_message": digest_text(str(exc)),
            "finished_at": utc_now(),
        }
        if isinstance(exc, SmokeContractError):
            payload.update(
                {"status_code": exc.status_code, "content_type": exc.content_type}
            )
        write_json(args.artifact_dir / error_name, payload)
        artifacts.append(str(error_name))
    append_command(
        args.artifact_dir,
        argv=[sys.executable, *sys.argv],
        exit_code=exit_code,
        started_at=started_at,
        finished_at=utc_now(),
        artifacts=artifacts,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
