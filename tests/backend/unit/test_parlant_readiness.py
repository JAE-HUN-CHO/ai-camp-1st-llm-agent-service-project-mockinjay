"""A listening port or wrong identity must never become ready."""

import asyncio
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
    checks = 0

    async def not_ready() -> bool:
        nonlocal checks
        checks += 1
        return False

    async def no_wait(_seconds) -> None:
        return None

    monkeypatch.setattr(agent_class, "_check_server_running", not_ready)
    monkeypatch.setattr(asyncio, "sleep", no_wait)
    monkeypatch.setattr(
        agent_class,
        "_parlant_server_process",
        SimpleNamespace(poll=lambda: None),
    )
    with pytest.raises(TimeoutError, match="failed to start"):
        await agent_class._ensure_server_running()
    assert checks > 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "agent_class"),
    [
        (research_module, research_module.ResearchPaperAgent),
        (welfare_module, welfare_module.MedicalWelfareAgent),
    ],
)
async def test_client_initialization_is_serialized(
    monkeypatch, module, agent_class
) -> None:
    initialized = 0
    setup_calls = 0
    release = asyncio.Event()

    async def ensure_ready() -> None:
        nonlocal initialized
        initialized += 1
        await release.wait()

    class _HTTPClient:
        async def aclose(self) -> None:
            return None

    class _ParlantClient:
        pass

    async def setup_agent() -> None:
        nonlocal setup_calls
        setup_calls += 1
        monkeypatch.setattr(agent_class, "_agent_id", "agent-1")

    monkeypatch.setattr(agent_class, "_parlant_client", None)
    monkeypatch.setattr(agent_class, "_agent_id", None)
    monkeypatch.setattr(agent_class, "_client_initialization_lock", None)
    monkeypatch.setattr(agent_class, "_client_initialization_loop", None)
    monkeypatch.setattr(agent_class, "_ensure_server_running", ensure_ready)
    monkeypatch.setattr(agent_class, "_setup_agent", setup_agent)
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_kwargs: _HTTPClient())
    monkeypatch.setattr(module, "AsyncParlantClient", lambda **_kwargs: _ParlantClient())

    first = asyncio.create_task(agent_class._get_client())
    await asyncio.sleep(0)
    second = asyncio.create_task(agent_class._get_client())
    await asyncio.sleep(0)
    assert initialized == 1

    release.set()
    first_client, second_client = await asyncio.gather(first, second)
    assert first_client is second_client
    assert initialized == 1
    assert setup_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_class",
    [research_module.ResearchPaperAgent, welfare_module.MedicalWelfareAgent],
)
async def test_client_initialization_rejects_event_loop_switch(
    monkeypatch, agent_class
) -> None:
    monkeypatch.setattr(agent_class, "_client_initialization_lock", None)
    monkeypatch.setattr(agent_class, "_client_initialization_loop", None)

    original_lock = agent_class._get_client_initialization_lock()
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: object())

    with pytest.raises(RuntimeError, match="single asyncio event loop"):
        agent_class._get_client_initialization_lock()
    assert agent_class._client_initialization_lock is original_lock
