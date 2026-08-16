"""A listening port or wrong identity must never become ready."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from Agent.medical_welfare import agent as welfare_module
from Agent.research_paper import agent as research_module


class _Response:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    def __init__(self, responses):
        self.responses = iter(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, *_args, **_kwargs):
        return next(self.responses)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "agent_class", "identity"),
    [
        (research_module, research_module.ResearchPaperAgent, "CareGuide_v2"),
        (welfare_module, welfare_module.MedicalWelfareAgent, "MedicalWelfare_Agent"),
    ],
)
async def test_readiness_requires_200_json_target_identity(monkeypatch, module, agent_class, identity) -> None:
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: _Client([_Response(404, {}), _Response(200, [{"id": "ag-1", "name": "wrong"}])]))
    assert await agent_class._check_server_running() is False

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: _Client([_Response(200, [{"id": "ag-1", "name": identity}])]))
    assert await agent_class._check_server_running() is True
