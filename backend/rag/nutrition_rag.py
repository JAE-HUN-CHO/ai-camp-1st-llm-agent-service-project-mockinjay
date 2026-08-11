"""
Nutrition RAG - local image encoder + MongoDB vector hybrid search
음식 이미지-텍스트 동시 검색을 위한 RAG 시스템
"""

import logging
from typing import List, Dict, Any, Optional, Union

import torch
from PIL import Image
from app.adapters.ollama.client import OllamaSyncClient

logger = logging.getLogger(__name__)


class KeywordScorer:
    """Small dependency-free scorer for the optional local keyword tier."""

    def __init__(self, corpus: list[list[str]]) -> None:
        self.corpus = corpus

    def get_scores(self, query: list[str]) -> list[float]:
        query_terms = set(query)
        return [float(sum(term in query_terms for term in document)) for document in self.corpus]


class NutritionRAG:
    """CLIP 기반 음식 검색 RAG - 이미지/텍스트 하이브리드 검색"""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Ollama is the only model provider. Ollama's embedding endpoint is
        # text-only, so the legacy image encoder is intentionally not loaded
        # from a hosted model at process startup.
        logger.info("NutritionRAG using local Ollama embeddings")
        self.embedding_client = OllamaSyncClient()

        # Hosted vector stores are not used. MongoDB Atlas Local is the
        # persistence target; this legacy CLIP surface remains read-only until
        # its Mongo vector adapter is wired in.
        self.pc = None
        self.index = None

        # Keyword scoring for the optional in-memory search tier
        self.bm25 = None
        self.food_corpus = []

    def _unflatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Vector metadata에서 nutrition 필드를 복원

        Args:
            metadata: Flattened metadata from the vector store

        Returns:
            Unflattened metadata with nutrition dict
        """
        nutrition = {}
        result = {}

        for key, value in metadata.items():
            if key.startswith("nutrition_"):
                # Extract nutrition field
                field_name = key.replace("nutrition_", "")
                nutrition[field_name] = value
            else:
                result[key] = value

        if nutrition:
            result["nutrition"] = nutrition

        return result

    def encode_image(self, image_input: Union[str, Image.Image]) -> torch.Tensor:
        """
        이미지를 CLIP 임베딩으로 변환

        Args:
            image_input: PIL Image 또는 base64 string

        Returns:
            CLIP image embedding (512-dim)
        """
        logger.error("Image encoding is disabled: Ollama's configured embedding model is text-only")
        raise RuntimeError(
            "Ollama's configured embedding model is text-only; image vector search is disabled"
        )

    def encode_text(self, text: str) -> torch.Tensor:
        """
        텍스트를 CLIP 임베딩으로 변환

        Args:
            text: 검색 쿼리 텍스트

        Returns:
            CLIP text embedding (512-dim)
        """
        try:
            response = self.embedding_client.embeddings.create(input=text)
            return torch.tensor(response.data[0].embedding)

        except Exception as e:
            logger.error(f"Text encoding failed: {e}")
            raise

    def search_by_image(
        self,
        image_input: Union[str, Image.Image],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        이미지로 유사 음식 검색

        Args:
            image_input: 음식 이미지 (PIL 또는 base64)
            top_k: 반환할 상위 결과 수

        Returns:
            List of {dish_name, ingredients, recipe, nutrition, score}
        """
        if not self.index:
            logger.warning("MongoDB vector adapter not available - using dummy data")
            return self._get_dummy_food_data(top_k)

        try:
            # Image embedding
            image_emb = self.encode_image(image_input)

            # MongoDB vector search
            results = self.index.query(
                vector=image_emb.tolist(),
                top_k=top_k,
                include_metadata=True
            )

            foods = []
            for match in results.matches:
                unflattened = self._unflatten_metadata(match.metadata)
                foods.append({
                    "dish_name": unflattened.get("dish_name", "Unknown"),
                    "ingredients": unflattened.get("ingredients", []),
                    "recipe": unflattened.get("recipe", ""),
                    "nutrition": unflattened.get("nutrition", {}),
                    "score": match.score
                })

            return foods

        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return self._get_dummy_food_data(top_k)

    def search_by_text(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        텍스트로 음식 검색 (시맨틱 검색)

        Args:
            query: 검색 쿼리 (음식명, 식재료 등)
            top_k: 반환할 상위 결과 수

        Returns:
            List of {dish_name, ingredients, recipe, nutrition, score}
        """
        if not self.index:
            logger.warning("MongoDB vector adapter not available - using dummy data")
            return self._get_dummy_food_data(top_k)

        try:
            # Text embedding
            text_emb = self.encode_text(query)

            # MongoDB vector search
            results = self.index.query(
                vector=text_emb.tolist(),
                top_k=top_k,
                include_metadata=True
            )

            foods = []
            for match in results.matches:
                unflattened = self._unflatten_metadata(match.metadata)
                foods.append({
                    "dish_name": unflattened.get("dish_name", "Unknown"),
                    "ingredients": unflattened.get("ingredients", []),
                    "recipe": unflattened.get("recipe", ""),
                    "nutrition": unflattened.get("nutrition", {}),
                    "score": match.score
                })

            return foods

        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return self._get_dummy_food_data(top_k)

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (시맨틱 + BM25 키워드)

        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
            semantic_weight: 시맨틱 검색 가중치 (0~1)

        Returns:
            List of {dish_name, ingredients, recipe, nutrition, score}
        """
        # Semantic search
        semantic_results = self.search_by_text(query, top_k=top_k * 2)

        # Keyword search (if a local corpus is loaded)
        if self.bm25 and self.food_corpus:
            tokenized_query = query.split()
            bm25_scores = self.bm25.get_scores(tokenized_query)

            # Combine scores
            combined = {}
            for idx, food in enumerate(self.food_corpus):
                dish_name = food["dish_name"]
                # Normalize BM25 scores
                bm25_score = bm25_scores[idx] / (max(bm25_scores) + 1e-6)

                # Find semantic score
                semantic_score = 0
                for sem_result in semantic_results:
                    if sem_result["dish_name"] == dish_name:
                        semantic_score = sem_result["score"]
                        break

                # Weighted combination
                combined[dish_name] = {
                    **food,
                    "score": semantic_weight * semantic_score + (1 - semantic_weight) * bm25_score
                }

            # Sort by combined score
            ranked = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
            return ranked[:top_k]

        else:
            # Fallback to semantic only
            return semantic_results[:top_k]

    def load_food_corpus(self, foods: List[Dict[str, Any]]):
        """
        로컬 keyword 검색을 위한 음식 코퍼스 로드

        Args:
            foods: List of {dish_name, ingredients, recipe, nutrition}
        """
        self.food_corpus = foods

        # Tokenize for the dependency-free keyword scorer
        corpus_texts = [
            f"{food['dish_name']} {' '.join(food.get('ingredients', []))} {food.get('recipe', '')}"
            for food in foods
        ]
        tokenized_corpus = [doc.split() for doc in corpus_texts]

        self.bm25 = KeywordScorer(tokenized_corpus)
        logger.info(f"📚 Keyword corpus loaded: {len(foods)} foods")

    def upsert_food(
        self,
        food_id: str,
        dish_name: str,
        ingredients: List[str],
        recipe: str,
        nutrition: Dict[str, Any],
        image: Optional[Image.Image] = None
    ):
        """
        음식 데이터를 MongoDB vector adapter에 전달

        Args:
            food_id: Unique ID
            dish_name: 요리명
            ingredients: 식재료 리스트
            recipe: 조리법
            nutrition: 영양 정보 {sodium, potassium, phosphorus, protein, calcium}
            image: 음식 이미지 (선택)
        """
        if not self.index:
            logger.warning("MongoDB vector adapter not available - skipping upsert")
            return

        try:
            # Generate embedding (image or text)
            if image:
                embedding = self.encode_image(image)
            else:
                # Fallback to text embedding
                text = f"{dish_name} {' '.join(ingredients)} {recipe}"
                embedding = self.encode_text(text)

            # Flatten nutrition metadata for vector storage
            metadata = {
                "dish_name": dish_name,
                "ingredients": ingredients,
                "recipe": recipe[:500] if recipe else "",  # Truncate long recipes
            }

            # Add flattened nutrition fields
            if nutrition:
                for key, value in nutrition.items():
                    metadata[f"nutrition_{key}"] = float(value) if value else 0.0

            # Upsert through the MongoDB vector adapter
            self.index.upsert(
                vectors=[(
                    food_id,
                    embedding.tolist(),
                    metadata
                )]
            )

            logger.info(f"✅ Upserted food: {dish_name} (ID: {food_id})")

        except Exception as e:
            logger.error(f"Upsert failed for {dish_name}: {e}")

    def _get_dummy_food_data(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """더미 음식 데이터 (RAG 비활성화 시)"""
        dummy_foods = [
            {
                "dish_name": "저염 닭가슴살 샐러드",
                "ingredients": ["닭가슴살", "양배추", "오이", "방울토마토", "올리브오일"],
                "recipe": "닭가슴살을 삶아 찢고, 데친 야채와 함께 올리브오일 드레싱으로 버무립니다.",
                "nutrition": {
                    "sodium": 350,
                    "potassium": 450,
                    "phosphorus": 180,
                    "protein": 28,
                    "calcium": 65
                },
                "score": 0.95
            },
            {
                "dish_name": "저인 계란 볶음밥",
                "ingredients": ["현미밥", "계란 흰자", "양파", "당근", "저염 간장"],
                "recipe": "현미밥에 계란 흰자와 야채를 넣고 저염 간장으로 간하여 볶습니다.",
                "nutrition": {
                    "sodium": 420,
                    "potassium": 380,
                    "phosphorus": 220,
                    "protein": 18,
                    "calcium": 45
                },
                "score": 0.88
            },
            {
                "dish_name": "저칼륨 야채 스프",
                "ingredients": ["양배추", "가지", "애호박", "당근", "허브"],
                "recipe": "야채를 데쳐 칼륨을 제거한 후 허브로 간을 하여 끓입니다.",
                "nutrition": {
                    "sodium": 280,
                    "potassium": 320,
                    "phosphorus": 95,
                    "protein": 8,
                    "calcium": 72
                },
                "score": 0.82
            }
        ]

        return dummy_foods[:top_k]
