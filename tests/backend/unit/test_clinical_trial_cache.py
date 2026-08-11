"""Regression guards for clinical-trial cache isolation and outage fallback."""

import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parents[3] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.api import clinical_trials


@pytest.fixture(autouse=True)
def clear_trial_cache():
    clinical_trials._trials_cache.clear()
    clinical_trials._translation_cache.clear()
    yield
    clinical_trials._trials_cache.clear()
    clinical_trials._translation_cache.clear()


def test_status_is_part_of_trial_cache_key() -> None:
    clinical_trials.set_cached_trials("kidney", 1, 10, {"status": "recruiting"}, "RECRUITING")

    assert clinical_trials.get_cached_trials("kidney", 1, 10, "RECRUITING") == {
        "status": "recruiting"
    }
    assert clinical_trials.get_cached_trials("kidney", 1, 10, "COMPLETED") is None


def test_translation_cache_expires_with_same_ttl_policy() -> None:
    clinical_trials.set_cached_translation("kidney", "신장")

    assert clinical_trials.get_cached_translation("kidney") == "신장"
    key = clinical_trials.get_text_hash("kidney")
    clinical_trials._translation_cache[key]["timestamp"] = 0

    assert clinical_trials.get_cached_translation("kidney") is None


def test_local_summary_client_is_configured() -> None:
    assert clinical_trials.get_ollama_client() is not None


@pytest.mark.asyncio
async def test_list_returns_stale_cache_when_provider_fails(monkeypatch) -> None:
    stale = {"status": "success", "trials": [], "total": 0}
    clinical_trials.set_cached_trials("kidney", 1, 10, stale)
    key = clinical_trials.get_cache_key("kidney", 1, 10)
    clinical_trials._trials_cache[key]["timestamp"] = 0

    async def provider_failure(**_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(clinical_trials, "fetch_clinical_trials", provider_failure)

    response = await clinical_trials.get_clinical_trials(
        clinical_trials.ClinicalTrialListRequest(condition="kidney", page=1, page_size=10)
    )

    assert response["trials"] == []
    assert response["stale"] is True
