"""Phase 3B Health Profile implementation selector tests."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.bootstrap.container import (
    HealthProfileConfigurationError,
    HealthProfileImplementation,
    HealthProfileTelemetry,
    build_health_profile_container,
    resolve_health_profile_implementation,
)


def test_health_profile_selector_defaults_to_legacy_when_unset() -> None:
    """Verify health profile selector defaults to legacy when unset."""
    assert resolve_health_profile_implementation({}) is HealthProfileImplementation.LEGACY


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_health_profile_selector_accepts_only_declared_values(implementation: str) -> None:
    """Verify health profile selector accepts only declared values."""
    assert resolve_health_profile_implementation(
        {"HEALTH_PROFILE_IMPLEMENTATION": implementation}
    ).value == implementation


def test_health_profile_selector_invalid_value_fails_closed() -> None:
    """Verify health profile selector invalid value fails closed."""
    with pytest.raises(HealthProfileConfigurationError):
        resolve_health_profile_implementation({"HEALTH_PROFILE_IMPLEMENTATION": "mongo"})


def test_health_profile_selector_can_rollback_to_unset_legacy() -> None:
    """Verify health profile selector can rollback to unset legacy."""
    selected = build_health_profile_container(
        environment={"HEALTH_PROFILE_IMPLEMENTATION": "hex"}
    )
    rolled_back = build_health_profile_container(environment={})

    assert selected.implementation is HealthProfileImplementation.HEX
    assert selected.get_health_profile is not None
    assert selected.update_health_profile is not None
    assert selected.legacy is None
    assert rolled_back.implementation is HealthProfileImplementation.LEGACY
    assert rolled_back.legacy is not None
    assert rolled_back.get_health_profile is None
    assert rolled_back.update_health_profile is None


def test_health_profile_telemetry_serializes_record_and_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify records cannot mutate counters while a snapshot is iterating."""
    telemetry = HealthProfileTelemetry(HealthProfileImplementation.HEX)
    telemetry.record("get", "success")
    snapshot_started = Event()
    allow_snapshot = Event()
    writer_started = Event()
    writer_finished = Event()
    original_items = Counter.items

    def blocking_items(counter: Counter[tuple[str, str]]):
        """Pause snapshot iteration so the concurrent writer can be observed."""
        for item in original_items(counter):
            snapshot_started.set()
            assert allow_snapshot.wait(timeout=1)
            yield item

    def record_once() -> None:
        """Attempt one record while the snapshot owns the telemetry lock."""
        writer_started.set()
        telemetry.record("get", "success")
        writer_finished.set()

    monkeypatch.setattr(Counter, "items", blocking_items)
    with ThreadPoolExecutor(max_workers=2) as executor:
        snapshot_future = executor.submit(telemetry.snapshot)
        assert snapshot_started.wait(timeout=1)
        writer_future = executor.submit(record_once)
        try:
            assert writer_started.wait(timeout=1)
            assert not writer_finished.wait(timeout=0.1)
        finally:
            allow_snapshot.set()

        assert snapshot_future.result(timeout=1)["counters"] == {"get.success": 1}
        writer_future.result(timeout=1)

    assert telemetry.snapshot()["counters"] == {"get.success": 2}
