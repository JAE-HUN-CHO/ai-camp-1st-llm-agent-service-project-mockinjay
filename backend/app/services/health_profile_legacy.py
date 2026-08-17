"""Compatibility facade for the frozen MyPage Health Profile REST v1 behavior."""

from __future__ import annotations

from datetime import datetime

from app.core.actor import ActorContext
from app.features.health.domain import (
    HealthProfile,
    HealthProfileAccessDenied,
    HealthProfilePatch,
)
from app.services.mypage.health_service import HealthService


def _owner_id(actor: ActorContext) -> str:
    """Require and return the authenticated legacy-profile owner identifier."""
    if not actor.user_id:
        raise HealthProfileAccessDenied
    return actor.user_id


class LegacyHealthProfileFacade:
    """Keep the pre-Phase-3B implementation available for restart rollback."""

    def __init__(self, service: HealthService | None = None) -> None:
        """Initialize the compatibility facade around the legacy service."""
        self._service = service or HealthService()

    async def get(self, actor: ActorContext) -> HealthProfile:
        """Load a legacy profile through the shared application-facing contract."""
        payload = await self._service.get_health_profile(_owner_id(actor))
        return self._to_domain(payload)

    async def update(
        self, actor: ActorContext, patch: HealthProfilePatch
    ) -> HealthProfile:
        """Update a legacy profile through the shared application-facing contract."""
        fields = patch.fields
        payload = await self._service.update_health_profile(
            _owner_id(actor),
            conditions=fields.get("conditions"),
            allergies=fields.get("allergies"),
            dietary_restrictions=fields.get("dietary_restrictions"),
            age=fields.get("age"),
            gender=fields.get("gender"),
        )
        return self._to_domain(payload)

    @staticmethod
    def _to_domain(payload: dict[str, object]) -> HealthProfile:
        """Convert the legacy payload to the shared health-profile domain model."""
        updated_at = payload.get("updatedAt")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        return HealthProfile(
            owner_id=str(payload["userId"]),
            conditions=tuple(payload.get("conditions", [])),
            allergies=tuple(payload.get("allergies", [])),
            dietary_restrictions=tuple(payload.get("dietaryRestrictions", [])),
            age=payload.get("age"),
            gender=payload.get("gender"),
            updated_at=updated_at,
        )
