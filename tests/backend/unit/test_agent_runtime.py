import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from backend.app.services.agent_runtime import AgentRuntime, get_agent_runtime
from backend.app.services.context_runtime import get_context_system
from backend.app.services.research_runtime import ResearchRuntime, get_research_runtime


def test_runtime_isolated_per_application_state():
    first = SimpleNamespace(state=SimpleNamespace())
    second = SimpleNamespace(state=SimpleNamespace())

    first_runtime = get_agent_runtime(SimpleNamespace(app=first))
    assert get_agent_runtime(SimpleNamespace(app=first)) is first_runtime
    assert get_agent_runtime(SimpleNamespace(app=second)) is not first_runtime


def test_runtime_can_be_injected_without_constructing_provider_agent():
    app = SimpleNamespace(state=SimpleNamespace(agent_runtime=AgentRuntime()))
    runtime = get_agent_runtime(SimpleNamespace(app=app))

    assert isinstance(runtime, AgentRuntime)


def test_context_runtime_isolated_per_application_state():
    first = SimpleNamespace(state=SimpleNamespace())
    second = SimpleNamespace(state=SimpleNamespace())

    first_context = get_context_system(SimpleNamespace(app=first))
    assert get_context_system(SimpleNamespace(app=first)) is first_context
    assert get_context_system(SimpleNamespace(app=second)) is not first_context


def test_research_runtime_isolated_per_application_state():
    first = SimpleNamespace(state=SimpleNamespace())
    second = SimpleNamespace(state=SimpleNamespace())

    first_research = get_research_runtime(SimpleNamespace(app=first))
    assert isinstance(first_research, ResearchRuntime)
    assert get_research_runtime(SimpleNamespace(app=first)) is first_research
    assert get_research_runtime(SimpleNamespace(app=second)) is not first_research
