"""Regression guard for administrative cache invalidation."""

import inspect
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

backend_dir = Path(__file__).resolve().parents[3] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.api.community import check_author_permission
from app.api.dependencies import require_admin
from app.api.news import clear_cache


def test_news_cache_clear_requires_admin_dependency() -> None:
    parameter = inspect.signature(clear_cache).parameters["admin_user_id"]

    assert parameter.default.dependency is require_admin


def test_community_mutation_rejects_non_owner() -> None:
    with pytest.raises(HTTPException) as exc_info:
        check_author_permission("user-a", "user-b", "update")

    assert exc_info.value.status_code == 403
