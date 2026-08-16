"""Phase 3B Health Profile implementation selector tests."""

import pytest

from app.bootstrap.container import (
    HealthProfileConfigurationError,
    HealthProfileImplementation,
    build_health_profile_container,
    resolve_health_profile_implementation,
)


def test_health_profile_selector_defaults_to_legacy_when_unset() -> None:
    assert resolve_health_profile_implementation({}) is HealthProfileImplementation.LEGACY


@pytest.mark.parametrize("implementation", ["legacy", "hex"])
def test_health_profile_selector_accepts_only_declared_values(implementation: str) -> None:
    assert resolve_health_profile_implementation(
        {"HEALTH_PROFILE_IMPLEMENTATION": implementation}
    ).value == implementation


def test_health_profile_selector_invalid_value_fails_closed() -> None:
    with pytest.raises(HealthProfileConfigurationError):
        resolve_health_profile_implementation({"HEALTH_PROFILE_IMPLEMENTATION": "mongo"})


def test_health_profile_selector_can_rollback_to_unset_legacy() -> None:
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
