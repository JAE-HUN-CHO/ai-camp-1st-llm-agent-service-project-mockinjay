"""Regression tests for health-record PATCH/null semantics.

These tests deliberately exercise the Pydantic contract without MongoDB so the
unit boundary stays deterministic and provider-independent.
"""

from backend.app.models.user_health_record import HealthRecordUpdate


def test_omitted_fields_are_excluded_from_patch_payload() -> None:
    update = HealthRecordUpdate(gfr=62.5)

    assert update.model_dump(exclude_unset=True) == {"gfr": 62.5}


def test_explicit_null_is_preserved_for_clearing_a_field() -> None:
    update = HealthRecordUpdate(memo=None)

    assert update.model_dump(exclude_unset=True) == {"memo": None}


def test_empty_patch_has_no_mutation_payload() -> None:
    update = HealthRecordUpdate()

    assert update.model_dump(exclude_unset=True) == {}
