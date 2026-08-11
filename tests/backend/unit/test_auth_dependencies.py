import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api import dependencies


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_secret(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "secret_key", "")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with pytest.raises(HTTPException) as error:
        await dependencies.get_current_user(credentials)

    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_malformed_token(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "secret_key", "test-secret")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")

    with pytest.raises(HTTPException) as error:
        await dependencies.get_current_user(credentials)

    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_require_admin_rejects_malformed_user_id(monkeypatch):
    with pytest.raises(HTTPException) as error:
        await dependencies.require_admin("not-an-object-id")

    assert error.value.status_code == 401
