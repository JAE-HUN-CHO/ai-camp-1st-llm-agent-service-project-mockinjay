"""Selector and rollback tests for the Phase 3A Health Records slice."""

import pytest

from app.bootstrap.container import (
    HealthRecordsConfigurationError,
    HealthRecordsImplementation,
    build_health_records_container,
    resolve_health_records_implementation,
)


def test_health_records_selector_defaults_to_legacy() -> None:
    assert resolve_health_records_implementation({}) is HealthRecordsImplementation.LEGACY


def test_health_records_selector_accepts_explicit_hex_and_legacy_rollback() -> None:
    assert resolve_health_records_implementation(
        {"HEALTH_RECORDS_IMPLEMENTATION": "hex"}
    ) is HealthRecordsImplementation.HEX
    assert resolve_health_records_implementation(
        {"HEALTH_RECORDS_IMPLEMENTATION": "legacy"}
    ) is HealthRecordsImplementation.LEGACY


def test_health_records_selector_rejects_invalid_value() -> None:
    with pytest.raises(HealthRecordsConfigurationError):
        resolve_health_records_implementation({"HEALTH_RECORDS_IMPLEMENTATION": "ollama"})


def test_health_records_container_builds_only_selected_path() -> None:
    legacy = build_health_records_container(environment={})
    hex_container = build_health_records_container(
        environment={"HEALTH_RECORDS_IMPLEMENTATION": "hex"}
    )

    assert legacy.is_hex is False
    assert legacy.legacy is not None
    assert legacy.list_health_records is None
    assert hex_container.is_hex is True
    assert hex_container.legacy is None
    assert hex_container.list_health_records is not None
