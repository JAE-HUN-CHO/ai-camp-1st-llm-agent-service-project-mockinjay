#!/usr/bin/env python3
"""Authenticated local HTTP smoke for the frozen MyPage Health Profile v1 API."""

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
    resolve_artifact_path,
    utc_now,
    write_json,
)
from verification_manifest import append_command


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "tests/backend/fixtures/health-profile-v1-contract.json").read_text(
        encoding="utf-8"
    )
)
PROFILE_KEYS = set(CONTRACT["response_keys"])


class SmokeContractError(RuntimeError):
    """Report only contract metadata, never a response body."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        content_type: str | None = None,
    ) -> None:
        """Initialize a redacted HTTP contract failure."""
        super().__init__(message)
        self.status_code = status_code
        self.content_type = content_type


def _json(
    response: httpx.Response, expected_status: int, expected_media_type: str
) -> object:
    """Validate JSON status and media type without retaining the raw body."""
    content_type = response.headers.get("content-type", "")
    if response.status_code != expected_status or expected_media_type not in content_type:
        raise SmokeContractError(
            "Health Profile status or media type mismatch",
            status_code=response.status_code,
            content_type=content_type,
        )
    try:
        return response.json()
    except ValueError as exc:
        raise SmokeContractError(
            "Health Profile response was not JSON",
            status_code=response.status_code,
            content_type=content_type,
        ) from exc


def _profile(
    response: httpx.Response, contract: dict[str, object]
) -> dict[str, object]:
    """Validate and return the frozen health-profile response shape."""
    payload = _json(
        response,
        int(contract["status"]),
        str(contract["media_type"]),
    )
    if not isinstance(payload, dict) or set(payload) != PROFILE_KEYS:
        raise SmokeContractError(
            "Health Profile response keys changed",
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
        )
    return payload


def _summary(response: httpx.Response, payload: object) -> dict[str, object]:
    """Summarize an HTTP response using status, media type, hash, and length."""
    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "body": digest_text(json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    }


def _stable_profile(profile: dict[str, object]) -> dict[str, object]:
    """Compare frozen profile values while allowing the write timestamp to advance."""
    return {key: value for key, value in profile.items() if key != "updatedAt"}


def run(args: argparse.Namespace) -> int:
    """Exercise owner, validation, and preservation cases over real local HTTP."""
    token = os.getenv("CAREGUIDE_SMOKE_TOKEN")
    other_token = os.getenv("CAREGUIDE_OTHER_SMOKE_TOKEN")
    canary = os.getenv("CAREGUIDE_HEALTH_PROFILE_CANARY")
    if not token or not other_token or not canary:
        raise RuntimeError("Health Profile smoke environment is incomplete")

    owner_id = jwt.get_unverified_claims(token).get("user_id")
    other_owner_id = jwt.get_unverified_claims(other_token).get("user_id")
    if not isinstance(owner_id, str) or not isinstance(other_owner_id, str):
        raise RuntimeError("Health Profile smoke owner claims are missing")

    base_url = require_local_http(args.base_url)
    artifact_path = resolve_artifact_path(args.artifact_dir, args.artifact_name)
    get_contract = CONTRACT["paths"]["get"]
    update_contract = CONTRACT["paths"]["update"]
    get_path = f"{base_url}{get_contract['path']}"
    update_path = f"{base_url}{update_contract['path']}"
    get_method = str(get_contract["method"])
    update_method = str(update_contract["method"])
    update_media_type = str(update_contract["media_type"])
    owner_headers = {"Authorization": f"Bearer {token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    operations: dict[str, object] = {}
    started_at = utc_now()
    cross_user_cases_passed = 0
    unauthorized_write_count = 1
    null_preserved = False
    unset_preserved = False
    validation_cases_passed = 0

    with httpx.Client(timeout=args.timeout) as client:
        default_response = client.request(get_method, get_path, headers=owner_headers)
        default_profile = _profile(default_response, get_contract)
        expected_default = {"userId": owner_id, **CONTRACT["default_values"]}
        if default_profile != expected_default:
            raise SmokeContractError("Health Profile default payload changed")
        operations["owner_default"] = _summary(default_response, default_profile)

        update_payload = {
            "conditions": [canary],
            "allergies": ["synthetic-allergy"],
            "dietaryRestrictions": ["synthetic-restriction"],
            "age": 44,
            "gender": "other",
        }
        if set(update_payload) != set(CONTRACT["update_fields"]):
            raise SmokeContractError("Health Profile update field set changed")
        update_response = client.request(
            update_method, update_path, headers=owner_headers, json=update_payload
        )
        updated = _profile(update_response, update_contract)
        if (
            updated.get("userId") != owner_id
            or updated.get("conditions") != [canary]
            or updated.get("healthConditions") != [canary]
            or updated.get("allergies") != ["synthetic-allergy"]
            or updated.get("dietaryRestrictions") != ["synthetic-restriction"]
            or updated.get("gender") != "other"
            or updated.get("age") != 44
            or not isinstance(updated.get("updatedAt"), str)
        ):
            raise SmokeContractError("Health Profile update payload changed")
        stable_updated = _stable_profile(updated)
        operations["owner_update"] = _summary(update_response, updated)

        null_response = client.request(
            update_method,
            update_path,
            headers=owner_headers,
            json={"conditions": None},
        )
        null_profile = _profile(null_response, update_contract)
        if _stable_profile(null_profile) != stable_updated:
            raise SmokeContractError("Health Profile explicit-null semantics changed")
        null_preserved = True
        operations["explicit_null"] = _summary(null_response, null_profile)

        unset_response = client.request(
            update_method, update_path, headers=owner_headers, json={}
        )
        unset_profile = _profile(unset_response, update_contract)
        if _stable_profile(unset_profile) != stable_updated:
            raise SmokeContractError("Health Profile unset semantics changed")
        owner_updated_at = unset_profile.get("updatedAt")
        if not isinstance(owner_updated_at, str):
            raise SmokeContractError("Health Profile update timestamp changed")
        unset_preserved = True
        operations["empty_update"] = _summary(unset_response, unset_profile)

        unauthenticated_response = client.request(
            update_method, update_path, json={"age": 45}
        )
        if unauthenticated_response.status_code not in {401, 403}:
            raise SmokeContractError(
                "Unauthenticated Health Profile write was accepted",
                status_code=unauthenticated_response.status_code,
                content_type=unauthenticated_response.headers.get("content-type"),
            )
        unauthenticated = _json(
            unauthenticated_response,
            401 if unauthenticated_response.status_code == 401 else 403,
            update_media_type,
        )
        operations["unauthenticated_update"] = _summary(
            unauthenticated_response, unauthenticated
        )
        unauthorized_write_count = 0

        other_default_response = client.request(
            get_method, get_path, headers=other_headers
        )
        other_default = _profile(other_default_response, get_contract)
        if other_default != {"userId": other_owner_id, **CONTRACT["default_values"]}:
            raise SmokeContractError("Cross-user Health Profile read leaked owner data")
        cross_user_cases_passed += 1
        operations["other_default"] = _summary(other_default_response, other_default)

        other_update_response = client.request(
            update_method,
            update_path,
            headers=other_headers,
            json={"age": 52, "gender": "other"},
        )
        other_updated = _profile(other_update_response, update_contract)
        if other_updated.get("userId") != other_owner_id or other_updated.get("age") != 52:
            raise SmokeContractError("Cross-user Health Profile owner binding failed")
        cross_user_cases_passed += 1
        operations["other_update"] = _summary(other_update_response, other_updated)

        owner_after_response = client.request(
            get_method, get_path, headers=owner_headers
        )
        owner_after = _profile(owner_after_response, get_contract)
        if (
            _stable_profile(owner_after) != stable_updated
            or owner_after.get("updatedAt") != owner_updated_at
        ):
            raise SmokeContractError("Cross-user Health Profile write changed owner data")
        cross_user_cases_passed += 1
        operations["owner_after_other_write"] = _summary(
            owner_after_response, owner_after
        )

        minimum_age = int(CONTRACT["validation"]["age_minimum"])
        maximum_age = int(CONTRACT["validation"]["age_maximum"])
        below_minimum_response = client.request(
            update_method,
            update_path,
            headers=owner_headers,
            json={"age": minimum_age - 1},
        )
        below_minimum = _json(
            below_minimum_response,
            int(CONTRACT["validation"]["age_below_minimum_status"]),
            update_media_type,
        )
        operations["invalid_age_below_minimum"] = _summary(
            below_minimum_response, below_minimum
        )
        validation_cases_passed += 1
        above_maximum_response = client.request(
            update_method,
            update_path,
            headers=owner_headers,
            json={"age": maximum_age + 1},
        )
        above_maximum = _json(
            above_maximum_response,
            int(CONTRACT["validation"]["age_above_maximum_status"]),
            update_media_type,
        )
        operations["invalid_age_above_maximum"] = _summary(
            above_maximum_response, above_maximum
        )
        validation_cases_passed += 1

        after_validation_response = client.request(
            get_method, get_path, headers=owner_headers
        )
        after_validation = _profile(after_validation_response, get_contract)
        if (
            _stable_profile(after_validation) != stable_updated
            or after_validation.get("updatedAt") != owner_updated_at
        ):
            raise SmokeContractError("Rejected Health Profile age was persisted")
        operations["owner_after_invalid_age"] = _summary(
            after_validation_response, after_validation
        )

    result = (
        "pass"
        if cross_user_cases_passed == 3
        and unauthorized_write_count == 0
        and null_preserved
        and unset_preserved
        and validation_cases_passed == 2
        else "fail"
    )

    write_json(
        artifact_path,
        {
            "schema_version": 1,
            "result": result,
            "implementation": args.implementation,
            "owner_id": digest_text(owner_id),
            "other_owner_id": digest_text(other_owner_id),
            "profile_keys": sorted(PROFILE_KEYS),
            "cross_user_cases": {"passed": cross_user_cases_passed, "total": 3},
            "unauthorized_write_count": unauthorized_write_count,
            "null_preserved": null_preserved,
            "unset_preserved": unset_preserved,
            "validation_cases": {"passed": validation_cases_passed, "total": 2},
            "operations": operations,
            "started_at": started_at,
            "finished_at": utc_now(),
        },
    )
    return 0 if result == "pass" else 1


def main() -> int:
    """Parse HTTP smoke arguments and return the contract result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--implementation", choices=("legacy", "hex"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--artifact-name", type=Path, required=True)
    args = parser.parse_args()
    args.artifact_dir = (args.artifact_dir or default_artifact_dir()).resolve()
    try:
        artifact_path = resolve_artifact_path(args.artifact_dir, args.artifact_name)
    except ValueError as exc:
        parser.error(str(exc))
    started_at = utc_now()
    exit_code = 0
    artifacts: list[str] = []
    try:
        exit_code = run(args)
        artifacts.append(str(args.artifact_name))
    except Exception as exc:
        exit_code = 1
        error_path = artifact_path.with_name(f"{artifact_path.stem}-error.json")
        payload: dict[str, object] = {
            "error_type": type(exc).__name__,
            "error_message": digest_text(str(exc)),
            "finished_at": utc_now(),
        }
        if isinstance(exc, SmokeContractError):
            payload.update(
                {"status_code": exc.status_code, "content_type": exc.content_type}
            )
        write_json(error_path, payload)
        artifacts.append(str(error_path.relative_to(args.artifact_dir)))
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
