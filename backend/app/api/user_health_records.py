"""Inbound FastAPI adapter for the frozen Health Records REST v1 contract."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import ActorContext, get_actor_context
from app.bootstrap.container import (
    HealthRecordsContainer,
    get_health_records_container,
)
from app.features.health.domain import (
    HealthRecord,
    HealthRecordAccessDenied,
    HealthRecordDraft,
    HealthRecordEmptyUpdate,
    HealthRecordNotFound,
    HealthRecordPatch,
)
from app.features.health import HEALTH_RECORDS_ROUTE_PREFIX
from app.models.user_health_record import (
    HealthRecordCreate,
    HealthRecordResponse,
    HealthRecordUpdate,
)


router = APIRouter(prefix=HEALTH_RECORDS_ROUTE_PREFIX, tags=["health-records"])


def _draft(record: HealthRecordCreate) -> HealthRecordDraft:
    return HealthRecordDraft(**record.model_dump())


def _patch(record: HealthRecordUpdate) -> HealthRecordPatch:
    return HealthRecordPatch(record.model_dump(exclude_unset=True))


def _response(record: HealthRecord) -> dict[str, object]:
    return {
        "id": record.record_id,
        "user_id": record.owner_id,
        "date": record.date,
        "hospital": record.hospital,
        "creatinine": record.creatinine,
        "gfr": record.gfr,
        "potassium": record.potassium,
        "phosphorus": record.phosphorus,
        "hemoglobin": record.hemoglobin,
        "albumin": record.albumin,
        "pth": record.pth,
        "hco3": record.hco3,
        "memo": record.memo,
    }


def _translate_health_record_error(error: Exception) -> HTTPException:
    if isinstance(error, HealthRecordNotFound):
        return HTTPException(status_code=404, detail="기록을 찾을 수 없습니다")
    if isinstance(error, HealthRecordEmptyUpdate):
        return HTTPException(status_code=400, detail="업데이트할 데이터가 없습니다")
    if isinstance(error, HealthRecordAccessDenied):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    raise error


@router.get("/", response_model=List[HealthRecordResponse])
async def get_health_records(
    actor: ActorContext = Depends(get_actor_context),
    container: HealthRecordsContainer = Depends(get_health_records_container),
):
    """Return the authenticated owner's records in descending date order."""
    operation = "list"
    try:
        if container.is_hex:
            if container.list_health_records is None:
                raise RuntimeError("Health Records hex container is incomplete")
            records = await container.list_health_records.execute(actor)
        else:
            if container.legacy is None:
                raise RuntimeError("Health Records legacy container is incomplete")
            records = await container.legacy.list(actor)
        container.telemetry.record(operation, "success")
        return [_response(record) for record in records]
    except Exception as error:
        container.telemetry.record(operation, "failure")
        raise _translate_health_record_error(error) from None


@router.post("/", response_model=HealthRecordResponse)
async def create_health_record(
    record: HealthRecordCreate,
    actor: ActorContext = Depends(get_actor_context),
    container: HealthRecordsContainer = Depends(get_health_records_container),
):
    """Create a record using the trusted JWT owner and frozen v1 payload."""
    operation = "create"
    try:
        draft = _draft(record)
        if container.is_hex:
            if container.create_health_record is None:
                raise RuntimeError("Health Records hex container is incomplete")
            created = await container.create_health_record.execute(actor, draft)
        else:
            if container.legacy is None:
                raise RuntimeError("Health Records legacy container is incomplete")
            created = await container.legacy.create(actor, draft)
        container.telemetry.record(operation, "success")
        return _response(created)
    except Exception as error:
        container.telemetry.record(operation, "failure")
        raise _translate_health_record_error(error) from None


@router.put("/{record_id}", response_model=HealthRecordResponse)
async def update_health_record(
    record_id: str,
    record_update: HealthRecordUpdate,
    actor: ActorContext = Depends(get_actor_context),
    container: HealthRecordsContainer = Depends(get_health_records_container),
):
    """Update an owner-scoped record while preserving null/unset semantics."""
    operation = "update"
    try:
        patch = _patch(record_update)
        if container.is_hex:
            if container.update_health_record is None:
                raise RuntimeError("Health Records hex container is incomplete")
            updated = await container.update_health_record.execute(actor, record_id, patch)
        else:
            if container.legacy is None:
                raise RuntimeError("Health Records legacy container is incomplete")
            updated = await container.legacy.update(actor, record_id, patch)
        container.telemetry.record(operation, "success")
        return _response(updated)
    except Exception as error:
        container.telemetry.record(operation, "failure")
        raise _translate_health_record_error(error) from None


@router.delete("/{record_id}")
async def delete_health_record(
    record_id: str,
    actor: ActorContext = Depends(get_actor_context),
    container: HealthRecordsContainer = Depends(get_health_records_container),
):
    """Delete only a record owned by the authenticated actor."""
    operation = "delete"
    try:
        if container.is_hex:
            if container.delete_health_record is None:
                raise RuntimeError("Health Records hex container is incomplete")
            await container.delete_health_record.execute(actor, record_id)
        else:
            if container.legacy is None:
                raise RuntimeError("Health Records legacy container is incomplete")
            await container.legacy.delete(actor, record_id)
        container.telemetry.record(operation, "success")
        return {"success": True, "message": "기록이 삭제되었습니다"}
    except Exception as error:
        container.telemetry.record(operation, "failure")
        raise _translate_health_record_error(error) from None
