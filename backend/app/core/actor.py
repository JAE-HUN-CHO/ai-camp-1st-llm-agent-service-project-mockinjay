"""Framework-independent identity propagated across application boundaries."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Trusted request actor and resources already bound to that actor."""

    user_id: str
    room_id: str | None = None
    session_id: str | None = None
    health_record_id: str | None = None
