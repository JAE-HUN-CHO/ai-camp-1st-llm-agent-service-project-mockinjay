"""Framework-independent values for the approved Health vertical slices."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType


MUTABLE_HEALTH_PROFILE_FIELDS = (
    "conditions",
    "allergies",
    "dietary_restrictions",
    "age",
    "gender",
)


class HealthProfileError(Exception):
    """Base failure translated by the MyPage inbound adapter."""


class HealthProfileAccessDenied(HealthProfileError):
    def __init__(self) -> None:
        """Initialize the fail-closed owner-access error."""
        super().__init__("authenticated actor is required")


class HealthProfilePersistenceError(HealthProfileError):
    def __init__(self) -> None:
        """Initialize the storage-boundary failure without sensitive values."""
        super().__init__("health profile persistence failed")


class HealthProfilePatchError(ValueError):
    def __init__(self) -> None:
        """Initialize the unsupported-patch-field error."""
        super().__init__("health profile patch contains unsupported fields")


@dataclass(frozen=True, slots=True)
class HealthProfile:
    """One owner-scoped document in the existing ``health_profiles`` collection."""

    owner_id: str
    conditions: tuple[str, ...] = ()
    allergies: tuple[str, ...] = ()
    dietary_restrictions: tuple[str, ...] = ()
    age: int | None = None
    gender: str | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Freeze mutable profile collections after construction."""
        object.__setattr__(self, "conditions", tuple(self.conditions))
        object.__setattr__(self, "allergies", tuple(self.allergies))
        object.__setattr__(
            self, "dietary_restrictions", tuple(self.dietary_restrictions)
        )

    @classmethod
    def empty(cls, owner_id: str) -> HealthProfile:
        """Create the frozen default profile for one owner."""
        return cls(owner_id=owner_id)

    def as_fields(self) -> dict[str, object]:
        """Return the profile fields using the existing storage schema names."""
        return {
            "conditions": self.conditions,
            "allergies": self.allergies,
            "dietary_restrictions": self.dietary_restrictions,
            "age": self.age,
            "gender": self.gender,
        }


@dataclass(frozen=True, slots=True)
class HealthProfilePatch:
    """Preserve v1 behavior: omitted and explicit-null values do not overwrite."""

    fields: Mapping[str, object]

    def __post_init__(self) -> None:
        """Validate patch fields and freeze the supplied mapping."""
        unknown = set(self.fields) - set(MUTABLE_HEALTH_PROFILE_FIELDS)
        if unknown:
            raise HealthProfilePatchError
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    def as_persisted_fields(self) -> dict[str, object]:
        """Return non-null fields that preserve the frozen update semantics."""
        return {key: value for key, value in self.fields.items() if value is not None}


OPTIONAL_HEALTH_RECORD_FIELDS = (
    "potassium",
    "phosphorus",
    "hemoglobin",
    "albumin",
    "pth",
    "hco3",
    "memo",
)
MUTABLE_HEALTH_RECORD_FIELDS = (
    "date",
    "hospital",
    "creatinine",
    "gfr",
    *OPTIONAL_HEALTH_RECORD_FIELDS,
)


@dataclass(frozen=True, slots=True)
class HealthRecordDraft:
    """Values accepted by the frozen v1 create contract."""

    date: str
    hospital: str
    creatinine: float
    gfr: float
    potassium: float | None = None
    phosphorus: float | None = None
    hemoglobin: float | None = None
    albumin: float | None = None
    pth: float | None = None
    hco3: float | None = None
    memo: str | None = None

    def as_fields(self) -> dict[str, str | float | None]:
        return {
            field: getattr(self, field) for field in MUTABLE_HEALTH_RECORD_FIELDS
        }


@dataclass(frozen=True, slots=True)
class HealthRecord:
    """One owner-scoped document in the existing ``health_records`` collection."""

    record_id: str
    owner_id: str
    date: str
    hospital: str
    creatinine: float
    gfr: float
    potassium: float | None = None
    phosphorus: float | None = None
    hemoglobin: float | None = None
    albumin: float | None = None
    pth: float | None = None
    hco3: float | None = None
    memo: str | None = None


@dataclass(frozen=True, slots=True)
class HealthRecordPatch:
    """Preserve the v1 distinction between omitted fields and explicit nulls."""

    fields: Mapping[str, object]

    def __post_init__(self) -> None:
        unknown = set(self.fields) - set(MUTABLE_HEALTH_RECORD_FIELDS)
        if unknown:
            raise ValueError("health record patch contains unsupported fields")
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))

    def as_fields(self) -> dict[str, object]:
        return dict(self.fields)

    @property
    def is_empty(self) -> bool:
        return not self.fields


class HealthRecordError(Exception):
    """Base failure translated by the Health Records inbound adapter."""


class HealthRecordAccessDenied(HealthRecordError):
    pass


class HealthRecordNotFound(HealthRecordError):
    pass


class HealthRecordEmptyUpdate(HealthRecordError):
    pass


class HealthRecordPersistenceError(HealthRecordError):
    pass
