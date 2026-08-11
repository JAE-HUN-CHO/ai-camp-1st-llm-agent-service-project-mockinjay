import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from app.api.dependencies import require_user_match
from app.api.rooms import _require_user_match


def test_room_identity_must_match_authenticated_subject() -> None:
    _require_user_match("user-1", "user-1")


def test_room_identity_mismatch_is_forbidden() -> None:
    with pytest.raises(HTTPException) as error:
        _require_user_match("user-1", "user-2")

    assert error.value.status_code == 403


def test_optional_history_filter_cannot_override_authenticated_subject() -> None:
    with pytest.raises(HTTPException) as error:
        require_user_match("user-2", "user-1")

    assert error.value.status_code == 403
