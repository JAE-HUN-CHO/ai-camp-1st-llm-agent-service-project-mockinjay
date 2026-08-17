"""Framework-independent Health Profile use-case tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.actor import ActorContext
from app.features.health.application import GetHealthProfile, UpdateHealthProfile
from app.features.health.domain import (
    HealthProfile,
    HealthProfileAccessDenied,
    HealthProfilePatch,
)


class _Repository:
    def __init__(self) -> None:
        """Initialize the owner-scoped fake repository state."""
        self.profiles: dict[str, HealthProfile] = {}
        self.read_owners: list[str] = []
        self.write_owners: list[str] = []

    async def get_for_owner(self, owner_id: str) -> HealthProfile:
        """Return the fake profile scoped to one owner."""
        self.read_owners.append(owner_id)
        return self.profiles.get(owner_id, HealthProfile.empty(owner_id))

    async def upsert_for_owner(
        self, owner_id: str, patch: HealthProfilePatch
    ) -> HealthProfile:
        """Persist one fake profile without crossing owner boundaries."""
        self.write_owners.append(owner_id)
        existing = self.profiles.get(owner_id, HealthProfile.empty(owner_id))
        values = existing.as_fields()
        values.update(patch.as_persisted_fields())
        profile = HealthProfile(
            owner_id=owner_id,
            updated_at=datetime.now(UTC),
            **values,
        )
        self.profiles[owner_id] = profile
        return profile


@pytest.mark.asyncio
async def test_get_health_profile_uses_only_actor_owner() -> None:
    """Verify get health profile uses only actor owner."""
    repository = _Repository()
    use_case = GetHealthProfile(repository)

    profile = await use_case.execute(ActorContext(user_id="actor-a"))

    assert profile == HealthProfile.empty("actor-a")
    assert repository.read_owners == ["actor-a"]
    assert repository.write_owners == []


@pytest.mark.asyncio
async def test_update_health_profile_preserves_null_and_unset_fields() -> None:
    """Verify update health profile preserves null and unset fields."""
    repository = _Repository()
    repository.profiles["actor-a"] = HealthProfile(
        owner_id="actor-a",
        conditions=("synthetic-condition",),
        allergies=("synthetic-allergy",),
        age=44,
    )
    use_case = UpdateHealthProfile(repository)

    profile = await use_case.execute(
        ActorContext(user_id="actor-a"),
        HealthProfilePatch({"conditions": None, "gender": "other"}),
    )

    assert profile.conditions == ("synthetic-condition",)
    assert profile.allergies == ("synthetic-allergy",)
    assert profile.age == 44
    assert profile.gender == "other"
    assert repository.write_owners == ["actor-a"]


@pytest.mark.asyncio
async def test_cross_user_updates_remain_separate() -> None:
    """Verify cross user updates remain separate."""
    repository = _Repository()
    use_case = UpdateHealthProfile(repository)

    await use_case.execute(
        ActorContext(user_id="actor-a"), HealthProfilePatch({"age": 41})
    )
    await use_case.execute(
        ActorContext(user_id="actor-b"), HealthProfilePatch({"age": 52})
    )

    assert repository.profiles["actor-a"].age == 41
    assert repository.profiles["actor-b"].age == 52
    assert repository.write_owners == ["actor-a", "actor-b"]


@pytest.mark.asyncio
async def test_missing_actor_fails_before_repository_calls() -> None:
    """Verify missing actor fails before repository calls."""
    repository = _Repository()

    with pytest.raises(HealthProfileAccessDenied):
        await UpdateHealthProfile(repository).execute(
            ActorContext(user_id=""), HealthProfilePatch({"age": 41})
        )

    assert repository.read_owners == []
    assert repository.write_owners == []
