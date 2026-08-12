"""Application-scoped Ollama chat service with MongoDB vector grounding.

The service is deliberately small: it owns the provider call used by the HTTP
chat contract and keeps retrieval close to generation so a response cannot be
described as RAG-backed when no vector context was actually collected.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from typing import Any

from app.adapters.ollama.client import OllamaClient, OllamaProviderError
from app.adapters.ollama.embedding import expand_vector_losslessly

EMERGENCY_RESPONSE = (
    "🚨 응급 증상이 의심됩니다. 즉시 119에 연락하거나 가까운 응급실로 이동하세요. "
    "온라인 안내만으로 진단하거나 기다리지 마세요."
)


class OllamaChatService:
    """Generate grounded chat answers using only the configured local Ollama."""

    def __init__(
        self,
        *,
        client: OllamaClient | Any | None = None,
        database: Any | None = None,
        collection_name: str | None = None,
        vector_index: str | None = None,
        top_k: int = 5,
    ) -> None:
        self.client = client or OllamaClient()
        self.database = database
        self.collection_name = collection_name or os.getenv(
            "MONGODB_VECTOR_COLLECTION", "pubmed_embeddings"
        )
        self.vector_index = vector_index or os.getenv(
            "MONGODB_VECTOR_INDEX", "vector_index"
        )
        self.dimensions = int(os.getenv("OLLAMA_EMBEDDING_DIMENSIONS", "1536"))
        self.top_k = max(1, min(top_k, 20))

    @staticmethod
    def _is_emergency(query: str) -> bool:
        # Keep the pre-filter independent from the LLM and avoid importing the
        # legacy agent graph when the service is used in a lightweight process.
        lowered = query.lower()
        return any(
            keyword in lowered
            for keyword in ("흉통", "가슴 통증", "호흡곤란", "숨이 안", "의식저하", "경련")
        )

    async def _embed(self, query: str) -> list[float]:
        response = await self.client.embeddings.create(
            model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe"),
            input=query,
        )
        data = getattr(response, "data", None) or []
        if len(data) != 1:
            raise OllamaProviderError("Ollama returned an invalid query embedding")
        vector = [float(value) for value in data[0].embedding]
        # Validate the persisted vector contract even when a custom client is
        # injected in tests. Only the documented 768 -> 1536 adapter is valid.
        if len(vector) != self.dimensions:
            vector = expand_vector_losslessly(vector, self.dimensions)
        if len(vector) != self.dimensions:
            raise OllamaProviderError(
                f"Query embedding must have {self.dimensions} dimensions"
            )
        return vector

    def _get_database(self) -> Any | None:
        if self.database is not None:
            return self.database
        try:
            from app.db.connection import Database

            return Database.db
        except (ImportError, AttributeError):
            return None

    async def retrieve(self, query_vector: list[float]) -> list[dict[str, Any]]:
        """Retrieve top vector matches from the accepted MongoDB collection."""
        database = self._get_database()
        if database is None:
            raise RuntimeError("MongoDB is not connected; vector retrieval is unavailable")

        collection = database[self.collection_name]
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.vector_index,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": max(self.top_k * 10, 50),
                    "limit": self.top_k,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "abstract": 1,
                    "text": 1,
                    "chunk_text": 1,
                    "source": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = collection.aggregate(pipeline)
        return await cursor.to_list(length=self.top_k)

    @staticmethod
    def _context_text(matches: list[Mapping[str, Any]]) -> str:
        sections: list[str] = []
        for index, match in enumerate(matches, start=1):
            metadata = match.get("metadata")
            metadata = metadata if isinstance(metadata, Mapping) else {}
            title = match.get("title") or metadata.get("title") or "자료"
            text = (
                match.get("chunk_text")
                or match.get("text")
                or match.get("abstract")
                or metadata.get("chunk_text")
                or metadata.get("text")
                or metadata.get("abstract")
                or ""
            )
            text = str(text).strip()
            if text:
                sections.append(f"[{index}] {title}\n{text[:1800]}")
        return "\n\n".join(sections)

    @staticmethod
    def _messages(query: str, context: str, profile: str, user_context: Any) -> list[dict[str, str]]:
        history = ""
        if isinstance(user_context, Mapping):
            summary = user_context.get("summary")
            keywords = user_context.get("keywords")
            if summary or keywords:
                history = f"\n사용자 컨텍스트: 요약={summary or ''}; 관심 주제={keywords or []}"
        system = (
            "당신은 CareGuide의 CKD 정보 보조자입니다. 반드시 한국어로 답하고, "
            "제공된 근거를 우선 사용하며 근거가 없으면 모른다고 말하세요. "
            "진단·처방을 단정하지 말고 필요하면 의료진 상담을 권고하세요. "
            f"사용자 프로필: {profile}.{history}"
        )
        grounded = context or "검색된 근거가 없습니다. 일반적인 의료 안전 원칙만 설명하세요."
        user = f"질문: {query}\n\n검색 근거:\n{grounded}"
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    async def generate(
        self,
        query: str,
        *,
        profile: str = "general",
        user_context: Any = None,
    ) -> dict[str, Any]:
        if self._is_emergency(query):
            return {
                "answer": EMERGENCY_RESPONSE,
                "sources": [],
                "metadata": {"provider": "emergency_pre_filter", "is_emergency": True},
            }

        vector = await self._embed(query)
        matches = await self.retrieve(vector)
        response = await self.client.chat.completions.create(
            model=os.getenv("OLLAMA_MODEL", "qwen3.6:27b-mlx"),
            messages=self._messages(query, self._context_text(matches), profile, user_context),
            temperature=0.2,
            max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "4096")),
        )
        answer = response.choices[0].message.content or ""
        return {
            "answer": answer,
            "sources": matches,
            "metadata": {
                "provider": "ollama",
                "generation_model": os.getenv("OLLAMA_MODEL", "qwen3.6:27b-mlx"),
                "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe"),
                "embedding_dimensions": self.dimensions,
                "retrieved_count": len(matches),
            },
        }

    async def stream(
        self,
        query: str,
        *,
        profile: str = "general",
        user_context: Any = None,
    ) -> AsyncIterator[dict[str, Any]]:
        if self._is_emergency(query):
            yield {"status": "complete", "content": EMERGENCY_RESPONSE, "agent_type": "ollama_rag", "is_emergency": True}
            return

        vector = await self._embed(query)
        matches = await self.retrieve(vector)
        yield {
            "status": "processing",
            "content": "근거를 검색하고 답변을 준비하고 있습니다…",
            "agent_type": "ollama_rag",
            "retrieved_count": len(matches),
        }
        stream = await self.client.chat.completions.create(
            model=os.getenv("OLLAMA_MODEL", "qwen3.6:27b-mlx"),
            messages=self._messages(query, self._context_text(matches), profile, user_context),
            temperature=0.2,
            max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "4096")),
            stream=True,
        )
        async for chunk in stream:
            content = getattr(getattr(chunk, "choices", [None])[0], "delta", None)
            content = getattr(content, "content", "") if content else ""
            if content:
                yield {"status": "streaming", "content": content, "agent_type": "ollama_rag"}

    async def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result
