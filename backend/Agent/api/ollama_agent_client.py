"""Agent-facing Ollama generation and embedding client."""

import logging
import os
from typing import Dict, List, Optional

from app.adapters.ollama.client import OllamaClient

logger = logging.getLogger(__name__)


class OllamaAgentClient:
    """Small domain client that talks only to the local Ollama adapter."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "qwen3.6:27b-mlx",
        embedding_model: str = "nomic-embed-text-v2-moe",
    ):
        self.client = OllamaClient(
            model=os.getenv("OLLAMA_MODEL", model),
            embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", embedding_model),
            base_url=base_url,
        )
        self.model = self.client.model
        self.embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", embedding_model)

    def count_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "text": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "model": self.model,
        }

    async def generate_nutrition_advice(
        self, query: str, nutrition_data: Dict, profile: str
    ) -> str:
        system_prompt = """당신은 전문 영양사입니다.
        환자의 건강 상태와 프로필을 고려하여 맞춤형 영양 조언을 제공합니다.
        과학적 근거를 바탕으로 명확하고 실용적인 조언을 제공하세요."""
        prompt = f"""
사용자 질문: {query}
사용자 프로필: {profile}

영양 데이터:
- 영양소: {nutrition_data.get('nutrients', {})}
- 제한사항: {nutrition_data.get('restrictions', [])}
- 권장사항: {nutrition_data.get('recommendations', [])}

위 정보를 바탕으로 맞춤형 영양 조언을 제공해주세요.
구체적인 식품 예시와 섭취량을 포함해주세요.
        """
        result = await self.generate(prompt, system_prompt, temperature=0.7)
        return result["text"]

    async def generate_medical_answer(
        self,
        query: str,
        search_results: List[Dict],
        papers: List[Dict],
        context: Dict,
    ) -> Dict:
        del context
        system_prompt = """당신은 의료 정보 전문가입니다.
        제공된 의료 데이터와 연구 논문을 바탕으로 정확하고 신뢰할 수 있는 답변을 제공합니다.
        항상 출처를 명시하고, 전문의 상담의 필요성을 언급하세요."""
        context_text = "검색 결과:\n"
        for i, result in enumerate(search_results[:5], 1):
            if "question" in result:
                context_text += f"{i}. Q: {result['question']}\n   A: {result.get('answer', '')[:200]}...\n"
            elif "title" in result:
                context_text += f"{i}. {result['title']}\n   {result.get('abstract', '')[:200]}...\n"
            else:
                context_text += f"{i}. {result.get('text', '')[:200]}...\n"
        if papers:
            context_text += "\n관련 연구 논문:\n"
            for i, paper in enumerate(papers[:3], 1):
                context_text += f"{i}. {paper.get('title', '')}\n   {paper.get('abstract', '')[:200]}...\n"
        result = await self.generate(
            f"사용자 질문: {query}\n\n{context_text}\n\n위 정보를 바탕으로 답변해주세요.",
            system_prompt,
            temperature=0.7,
        )
        return {"text": result["text"], "tokens": result["tokens_used"]}

    async def create_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.embedding_model, input=text
        )
        return response.data[0].embedding

    async def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(
            model=self.embedding_model, input=texts
        )
        return [item.embedding for item in response.data]
