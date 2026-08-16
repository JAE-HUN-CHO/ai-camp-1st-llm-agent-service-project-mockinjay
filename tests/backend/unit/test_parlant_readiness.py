"""A listening port or wrong identity must never become ready."""

import sys
from pathlib import Path
from types import SimpleNamespace

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
        self.call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, *_args, **_kwargs):
        self.call_count += 1
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
    wrong_client = _Client(
        [_Response(404, {}), _Response(200, [{"id": "ag-1", "name": "wrong"}])]
    )
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: wrong_client)
    assert await agent_class._check_server_running() is False
    assert wrong_client.call_count == 2

    ready_client = _Client([_Response(200, [{"id": "ag-1", "name": identity}])])
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: ready_client)
    assert await agent_class._check_server_running() is True
    assert ready_client.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agent_class", "identity"),
    [
        (research_module.ResearchPaperAgent, "CareGuide_v2"),
        (welfare_module.MedicalWelfareAgent, "MedicalWelfare_Agent"),
    ],
)
async def test_setup_never_falls_back_to_wrong_agent(monkeypatch, agent_class, identity) -> None:
    class _Agents:
        async def list(self):
            return [SimpleNamespace(id="wrong-id", name="wrong-agent")]

    monkeypatch.setattr(agent_class, "_parlant_client", SimpleNamespace(agents=_Agents()))
    with pytest.raises(ValueError, match=identity):
        await agent_class._setup_agent()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_class",
    [research_module.ResearchPaperAgent, welfare_module.MedicalWelfareAgent],
)
async def test_existing_process_is_not_ready_without_expected_identity(
    monkeypatch, agent_class
) -> None:
    async def not_ready():
        return False

    monkeypatch.setattr(agent_class, "_check_server_running", not_ready)
    monkeypatch.setattr(
        agent_class,
        "_parlant_server_process",
        SimpleNamespace(poll=lambda: None),
    )
    with pytest.raises(RuntimeError, match="expected agent identity"):
        await agent_class._ensure_server_running()
