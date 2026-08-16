"""Framework-independent Health Record values for the Phase 3A slice."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


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
