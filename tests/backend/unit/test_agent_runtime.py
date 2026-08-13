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


def test_runtime_returns_no_ollama_service_when_disabled(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "false")

    runtime = AgentRuntime()

    assert runtime.use_ollama is False
    assert runtime.chat_service is None


def test_runtime_uses_explicit_ollama_service_contract(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "true")

    runtime = AgentRuntime()

    assert runtime.use_ollama is True


def test_chat_service_is_lazy_and_cached(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "true")
    from app.services import ollama_chat

    constructed = []

    class FakeChatService:
        def __init__(self) -> None:
            constructed.append(self)

    monkeypatch.setattr(ollama_chat, "OllamaChatService", FakeChatService)
    runtime = AgentRuntime()
    assert constructed == []
    first = runtime.chat_service
    second = runtime.chat_service
    assert first is second
    assert len(constructed) == 1


def test_disabled_runtime_never_constructs_chat_service(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    from app.services import ollama_chat

    monkeypatch.setattr(ollama_chat, "OllamaChatService", lambda: (_ for _ in ()).throw(AssertionError("constructed")))
    assert AgentRuntime().chat_service is None


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
