"""Application-scoped agent runtime.

Agent instances hold mutable caches and provider clients.  Keeping them on the
FastAPI application state prevents imports from creating process-global
instances and gives tests an isolated runtime per application.
"""

from __future__ import annotations

from typing import Any


class AgentRuntime:
    """Lazily owns the agents used by HTTP routes for one app instance."""

    def __init__(self) -> None:
        self.use_ollama = True
        self._router_agent: Any | None = None
        self._nutrition_agent: Any | None = None
        self._agent_manager: Any | None = None
        self._chat_service: Any | None = None

    @property
    def chat_service(self) -> Any:
        """Return the application-scoped, real Ollama/RAG chat service."""
        if self._chat_service is None:
            from app.services.ollama_chat import OllamaChatService

            self._chat_service = OllamaChatService()
        return self._chat_service

    @property
    def router_agent(self) -> Any:
        if self._router_agent is None:
            from Agent.router.agent import RouterAgent

            self._router_agent = RouterAgent()
        return self._router_agent

    @property
    def nutrition_agent(self) -> Any:
        if self._nutrition_agent is None:
            from Agent.nutrition.agent import NutritionAgent

            self._nutrition_agent = NutritionAgent()
        return self._nutrition_agent

    @property
    def agent_manager(self) -> Any:
        if self._agent_manager is None:
            from Agent.agent_manager import AgentManager

            self._agent_manager = AgentManager()
        return self._agent_manager

    async def close(self) -> None:
        """Close provider clients owned by lazily-created agents."""
        for agent in (self._router_agent, self._nutrition_agent):
            if agent is None:
                continue
            close = getattr(getattr(agent, "client", None), "close", None)
            if close is not None:
                await close()
        if self._chat_service is not None:
            close = getattr(self._chat_service, "close", None)
            if close is not None:
                await close()
            self._chat_service = None


def get_agent_runtime(request: Any) -> AgentRuntime:
    """Return the runtime attached to the current FastAPI application."""
    runtime = getattr(request.app.state, "agent_runtime", None)
    if runtime is None:
        runtime = AgentRuntime()
        request.app.state.agent_runtime = runtime
    return runtime
