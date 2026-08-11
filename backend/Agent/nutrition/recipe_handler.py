"""
Recipe Handler - 레시피 생성 요청 처리
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Recipe generator
try:
    from tools.recipe_generator import get_recipe_generator
    RECIPE_GENERATOR_AVAILABLE = True
except ImportError:
    RECIPE_GENERATOR_AVAILABLE = False


class RecipeHandler:
    """레시피 생성 요청 처리"""

    # 하드코딩된 대표 레시피들
    COMMON_RECIPES = {
        "김치": {
            "recipe_name": "김치",
            "ingredients": ["배추", "소금", "고춧가루", "마늘", "생강", "파", "멸치액젓"],
            "cooking_method": "배추를 소금에 절인 후, 양념을 버무려 발효시킵니다."
        },
        "된장찌개": {
            "recipe_name": "된장찌개",
            "ingredients": ["된장", "두부", "애호박", "양파", "감자", "고춧가루", "마늘"],
            "cooking_method": "멸치 육수에 된장을 풀고 재료를 넣어 끓입니다."
        },
        "김치찌개": {
            "recipe_name": "김치찌개",
            "ingredients": ["배추김치", "돼지고기", "두부", "고춧가루", "파"],
            "cooking_method": "김치와 돼지고기를 볶다가 물을 넣고 끓입니다."
        }
    }

    def __init__(self, client, rag=None):
        self.client = client  # Ollama-compatible client
        self.rag = rag  # MongoDB vector RAG

    async def handle_recipe_request(
        self,
        user_query: str,
        session_id: str,
        conv_state: Dict[str, Any],
        user_profile: str = "general"
    ) -> Dict[str, Any]:
        """
        레시피 생성 요청 처리 (예: "저염식 김치 레시피")

        Args:
            user_query: 사용자 질문
            session_id: 세션 ID
            conv_state: 대화 상태
            user_profile: 사용자 프로필

        Returns:
            레시피 텍스트 (nutritionData 없음)
        """
        if not RECIPE_GENERATOR_AVAILABLE:
            logger.warning("Recipe generator not available")
            return None

        try:
            # 1. 레시피 이름 추출 (예: "저염식 김치 레시피" -> "김치")
            recipe_name = self._extract_recipe_name(user_query)
            logger.info(f"🍽️  Recipe request for: {recipe_name}")

            # 2. 사용자 프로필 정보 가져오기
            user_profile_data = conv_state.get("user_profile_data", {
                "ckd_stage": "default"
            })

            # 3. 원본 레시피 정보 가져오기 (RAG 또는 하드코딩)
            original_recipe = await self._get_original_recipe(recipe_name)

            if not original_recipe:
                logger.warning(f"Original recipe not found for: {recipe_name}")
                return {
                    "response": f"{recipe_name} 레시피를 찾을 수 없습니다. 다른 요리를 요청해주세요.",
                    "nutritionData": None
                }

            logger.info(f"Original recipe: {original_recipe['ingredients']}")

            # 4. RecipeGenerator로 저염식/저칼륨/저인 레시피 생성
            recipe_gen = get_recipe_generator()
            modified_recipe = recipe_gen.generate_low_nutrient_recipe(
                original_recipe_name=recipe_name,
                original_ingredients=original_recipe["ingredients"],
                user_profile=user_profile_data
            )

            logger.info(f"Generated {len(modified_recipe['substitutions'])} substitutions")

            # 5. LLM으로 최종 레시피 텍스트 생성
            recipe_text = await self._generate_recipe_text_with_llm(
                recipe_name=recipe_name,
                modified_recipe=modified_recipe,
                original_recipe=original_recipe,
                user_profile=user_profile
            )

            return {
                "response": recipe_text,
                "nutritionData": None,  # 레시피는 영양소 차트 없이 텍스트만
                "recipeData": {
                    "recipe_name": modified_recipe["recipe_name"],
                    "substitutions": modified_recipe["substitutions"],
                    "modified_ingredients": modified_recipe["modified_ingredients"]
                }
            }

        except Exception as e:
            logger.error(f"Recipe generation failed: {e}", exc_info=True)
            return {
                "response": f"레시피 생성 중 오류가 발생했습니다: {str(e)}",
                "nutritionData": None
            }

    def _extract_recipe_name(self, user_query: str) -> str:
        """
        쿼리에서 레시피 이름 추출

        Examples:
            "저염식 김치 레시피" -> "김치"
            "저칼륨 된장찌개 만드는 법" -> "된장찌개"
        """
        # 불필요한 키워드 제거
        keywords_to_remove = [
            "저염식", "저칼륨", "저인", "저단백",
            "레시피", "만들기", "만드는법", "만드는 법", "요리법",
            "어떻게", "알려줘", "알려주세요", "추천", " "
        ]

        recipe_name = user_query
        for keyword in keywords_to_remove:
            recipe_name = recipe_name.replace(keyword, "")

        recipe_name = recipe_name.strip()
        return recipe_name

    async def _get_original_recipe(self, recipe_name: str) -> Optional[Dict[str, Any]]:
        """
        원본 레시피 정보 가져오기 (RAG 또는 하드코딩)

        Returns:
            {
                "recipe_name": "김치",
                "ingredients": ["배추", "소금", "고춧가루", "마늘", "생강", "파"],
                "cooking_method": "..."
            }
        """
        # 하드코딩된 레시피 먼저 확인
        if recipe_name in self.COMMON_RECIPES:
            return self.COMMON_RECIPES[recipe_name]

        # RAG에서 검색 시도
        if self.rag:
            try:
                results = self.rag.search_by_text(recipe_name, top_k=1)
                if results and len(results) > 0:
                    top_result = results[0]
                    return {
                        "recipe_name": top_result["dish_name"],
                        "ingredients": top_result.get("ingredients", []),
                        "cooking_method": top_result.get("recipe", "")
                    }
            except Exception as e:
                logger.error(f"RAG search failed: {e}")

        return None

    async def _generate_recipe_text_with_llm(
        self,
        recipe_name: str,
        modified_recipe: Dict[str, Any],
        original_recipe: Dict[str, Any],
        user_profile: str = "general"
    ) -> str:
        """
        LLM으로 최종 레시피 텍스트 생성

        Args:
            recipe_name: 레시피 이름
            modified_recipe: 수정된 레시피 (substitutions 포함)
            original_recipe: 원본 레시피
            user_profile: 사용자 프로필

        Returns:
            친절한 레시피 텍스트
        """
        try:
            # 대체 정보 포맷팅
            substitution_text = ""
            if modified_recipe["substitutions"]:
                substitution_text = "\n\n**식재료 변경:**\n"
                for sub in modified_recipe["substitutions"]:
                    orig_nutrients = sub["original_nutrients"]
                    repl_nutrients = sub["replacement_nutrients"]
                    substitution_text += (
                        f"- ❌ {sub['original']} (Na={orig_nutrients['sodium']}mg, K={orig_nutrients['potassium']}mg) "
                        f"→ ✅ {sub['replacement']} (Na={repl_nutrients['sodium']}mg, K={repl_nutrients['potassium']}mg)\n"
                        f"  💡 이유: {sub['reason']}\n"
                    )

            # 최종 식재료 리스트
            ingredients_list = ", ".join(modified_recipe["modified_ingredients"])

            # LLM 프롬프트
            prompt = f"""당신은 만성 신장병 환자를 위한 영양 전문가입니다.

사용자가 "{recipe_name} 레시피"를 요청했습니다.

**환자 정보:**
- CKD 단계: {modified_recipe['ckd_stage']}
- 1일 1식 목표: 나트륨 {modified_recipe['user_limits']['sodium']}mg, 칼륨 {modified_recipe['user_limits']['potassium']}mg, 인 {modified_recipe['user_limits']['phosphorus']}mg

**원본 레시피:**
- 식재료: {', '.join(original_recipe['ingredients'])}

**수정된 레시피 (저염식/저칼륨/저인):**
- 식재료: {ingredients_list}
{substitution_text}

**요청사항:**
1. 사용자 프로필에 맞게 친절하게 인사하기
2. 왜 일부 식재료를 변경했는지 설명하기 (신장 건강에 미치는 영향)
3. 수정된 식재료로 조리하는 방법 상세히 설명하기
4. 맛을 유지하면서 나트륨/칼륨/인을 줄이는 조리 팁 추가하기
5. 신장병 환자를 위한 주의사항 안내하기

**응답 형식:**
- 자연스러운 대화체로 작성
- 영양소 수치는 적절히 언급 (과도하지 않게)
- 따뜻하고 격려하는 톤
- 반드시 한국어로만 작성

지금 바로 레시피를 작성해주세요."""

            response = await self.client.chat.completions.create(
                model=os.getenv("OLLAMA_MODEL", "qwen3.6:27b-mlx"),
                messages=[
                    {"role": "system", "content": "당신은 신장병 환자를 위한 영양 전문가입니다. 저염식/저칼륨/저인 레시피를 작성합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )

            recipe_text = response.choices[0].message.content
            logger.info(f"✅ Recipe text generated: {len(recipe_text)} chars")

            return recipe_text

        except Exception as e:
            logger.error(f"LLM recipe generation failed: {e}")
            # Fallback to simple text
            return self._generate_simple_recipe_text(recipe_name, modified_recipe)

    def _generate_simple_recipe_text(
        self,
        recipe_name: str,
        modified_recipe: Dict[str, Any]
    ) -> str:
        """LLM 실패 시 간단한 레시피 텍스트 생성"""
        text = f"# {modified_recipe['recipe_name']}\n\n"
        text += f"신장병 환자분을 위한 저염식 레시피입니다.\n\n"

        if modified_recipe["substitutions"]:
            text += "**식재료 변경:**\n"
            for sub in modified_recipe["substitutions"]:
                text += f"- {sub['original']} → {sub['replacement']} ({sub['reason']})\n"

        text += f"\n**최종 식재료:** {', '.join(modified_recipe['modified_ingredients'])}\n"
        text += "\n수정된 식재료로 기존과 동일하게 조리하시면 됩니다."

        return text

    @staticmethod
    def is_recipe_request(user_query: str) -> bool:
        """레시피 요청인지 확인"""
        recipe_keywords = ["레시피", "만들기", "만드는법", "만드는 법", "요리법", "조리법"]
        return any(keyword in user_query for keyword in recipe_keywords)
