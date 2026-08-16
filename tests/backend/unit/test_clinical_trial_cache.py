"""Regression guards for clinical-trial cache isolation and outage fallback."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

backend_dir = Path(__file__).resolve().parents[3] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.api import clinical_trials


class _AsyncCacheCollection:
    def __init__(self) -> None:
        self.entries = {}

    async def find_one(self, query):
        return self.entries.get(query["cache_key"])

    async def update_one(self, query, update, upsert=False):
        assert upsert is True
        self.entries[query["cache_key"]] = update["$set"]


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


def test_trial_cache_key_is_namespaced_by_source_contract() -> None:
    key = clinical_trials.get_cache_key("kidney", 1, 10)
    assert key.startswith(f"{clinical_trials.CACHE_CONTRACT_VERSION}:")


def test_translation_cache_expires_with_same_ttl_policy() -> None:
    clinical_trials.set_cached_translation("kidney", "신장")

    assert clinical_trials.get_cached_translation("kidney") == "신장"
    key = clinical_trials.get_text_hash("kidney")
    clinical_trials._translation_cache[key]["timestamp"] = 0

    assert clinical_trials.get_cached_translation("kidney") is None


def test_local_translation_client_is_configured() -> None:
    assert clinical_trials.get_ollama_client() is not None


@pytest.mark.asyncio
async def test_detail_contract_preserves_source_and_forbids_generated_interpretation(monkeypatch) -> None:
    async def fake_detail(_nct_id):
        return {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}

    async def fake_parse(_study, *, translate=False):
        return {
            "nctId": "NCT00000001",
            "title": "충실한 번역" if translate else "Recommendations and clinical significance",
        }

    monkeypatch.setattr(clinical_trials, "fetch_trial_detail", fake_detail)
    monkeypatch.setattr(clinical_trials, "parse_trial_data", fake_parse)

    response = await clinical_trials.get_trial_detail(
        clinical_trials.ClinicalTrialDetailRequest(nct_id="NCT00000001", language="ko")
    )

    assert response["trial"]["title"] == "Recommendations and clinical significance"
    assert response["translation"]["title"] == "충실한 번역"
    assert response["source"]["url"].endswith("NCT00000001")
    assert response["informationOnly"] is True
    assert response["disclaimer"]
    assert {"aiSummary", "recommendations", "clinicalSignificance"}.isdisjoint(response)


@pytest.mark.asyncio
async def test_english_detail_skips_translation(monkeypatch) -> None:
    calls = []

    async def fake_detail(_nct_id):
        return {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}

    async def fake_parse(_study, *, translate=False):
        calls.append(translate)
        return {"nctId": "NCT00000001", "title": "Original title"}

    monkeypatch.setattr(clinical_trials, "fetch_trial_detail", fake_detail)
    monkeypatch.setattr(clinical_trials, "parse_trial_data", fake_parse)
    response = await clinical_trials.get_trial_detail(
        clinical_trials.ClinicalTrialDetailRequest(nct_id="NCT00000001", language="en")
    )

    assert calls == [False]
    assert response["translation"] == response["trial"]


def test_detail_request_rejects_unsupported_language() -> None:
    with pytest.raises(ValidationError):
        clinical_trials.ClinicalTrialDetailRequest(nct_id="NCT00000001", language="ja")


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


@pytest.mark.asyncio
async def test_provider_walks_clinical_trials_next_page_token(monkeypatch) -> None:
    requests = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url, params):
            requests.append(params)
            if len(requests) == 1:
                return FakeResponse({"studies": [], "totalCount": 25, "nextPageToken": "page-2"})
            return FakeResponse({"studies": []})

    monkeypatch.setattr(clinical_trials.httpx, "AsyncClient", lambda **_kwargs: FakeClient())

    data = await clinical_trials.fetch_clinical_trials(page=2, page_size=10)

    assert len(requests) == 2
    assert requests[0]["countTotal"] == "true"
    assert "pageToken" not in requests[0]
    assert requests[1]["pageToken"] == "page-2"
    assert "countTotal" not in requests[1]
    assert data["totalCount"] == 25


@pytest.mark.asyncio
async def test_persistent_cache_round_trip_uses_shared_mongo_tier(monkeypatch) -> None:
    collection = _AsyncCacheCollection()
    monkeypatch.setattr(clinical_trials, "get_clinical_trials_cache_collection", lambda: collection)

    await clinical_trials.set_persistent_cache("trials:kidney", {"trials": []})

    assert await clinical_trials.get_persistent_cache("trials:kidney") == {"trials": []}
    assert collection.entries["trials:kidney"]["expires_at"] > collection.entries["trials:kidney"]["fresh_until"]
