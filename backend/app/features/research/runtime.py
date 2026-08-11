"""Application-scoped research/trends provider runtime."""

from __future__ import annotations

from typing import Any


class ResearchRuntime:
    """Lazy owners for provider clients used by research routes."""

    def __init__(self) -> None:
        self._trend_agent: Any | None = None
        self._summarization_service: Any | None = None
        self._pubmed_client: Any | None = None
        self._news_scraper: Any | None = None

    @property
    def trend_agent(self) -> Any:
        if self._trend_agent is None:
            from Agent.trend_visualization.agent import TrendVisualizationAgent

            self._trend_agent = TrendVisualizationAgent()
        return self._trend_agent

    @property
    def summarization_service(self) -> Any:
        if self._summarization_service is None:
            from app.services.summarization import PaperSummarizationService

            self._summarization_service = PaperSummarizationService()
        return self._summarization_service

    @property
    def pubmed_client(self) -> Any:
        if self._pubmed_client is None:
            from Agent.api.pubmed_client import PubMedClient

            self._pubmed_client = PubMedClient()
        return self._pubmed_client

    @property
    def news_scraper(self) -> Any:
        if self._news_scraper is None:
            from app.services.news_scraper import NewsScraperService

            self._news_scraper = NewsScraperService()
        return self._news_scraper

    async def close(self) -> None:
        if self._trend_agent is not None:
            await self._trend_agent.close()
        if self._pubmed_client is not None:
            self._pubmed_client.close()


def get_research_runtime(request: Any) -> ResearchRuntime:
    runtime = getattr(request.app.state, "research_runtime", None)
    if runtime is None:
        runtime = ResearchRuntime()
        request.app.state.research_runtime = runtime
    return runtime
