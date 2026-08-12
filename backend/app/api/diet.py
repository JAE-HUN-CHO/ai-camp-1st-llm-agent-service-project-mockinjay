from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request
from typing import Optional
import logging
from Agent.core.contracts import AgentRequest
from app.features.chat.runtime import get_context_system
from app.services.agent_runtime import get_agent_runtime
from app.utils.upload import read_validated_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diet-care", tags=["Diet Care"])

async def _analyze_nutrition_internal(
    http_request: Request,
    session_id: str,
    text: Optional[str],
    user_profile: str,
    image: Optional[UploadFile]
):
    """Internal nutrition analysis logic shared by both endpoints"""
    logger.info(f"📝 Nutrition analysis request: session={session_id}, profile={user_profile}, has_text={bool(text)}, has_image={bool(image)}")

    # Validate that either text or image is provided
    if not text and not image:
        raise HTTPException(status_code=400, detail="Either text or image is required")

    # Check session
    context_system = get_context_system(http_request)
    session = context_system.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # 이미지가 있고, 실제 파일인 경우에만 base64로 인코딩
    image_data = None
    if image and image.filename:  # Check if image has a filename (actual file uploaded)
        import base64
        contents = await read_validated_image(image)
        image_data = base64.b64encode(contents).decode('utf-8')
        logger.info("🖼️ Validated nutrition image uploaded (%d base64 bytes)", len(image_data))

    context = {
        "image_data": image_data,
        "has_image": image is not None and image.filename is not None,
        "user_profile": user_profile  # Pass user profile to agent
    }

    user_input = text or "음식 이미지 분석 요청"

    try:
        # Create AgentRequest for the nutrition agent
        agent_request = AgentRequest(
            query=user_input,
            session_id=session_id,
            context=context,
            profile=user_profile
        )

        # Call nutrition agent with AgentRequest
        response = await get_agent_runtime(http_request).nutrition_agent.process(agent_request)

        logger.info(f"✅ Nutrition analysis complete: {response.status}")

        return {
            "success": response.status != "error",
            "agent_type": "nutrition",
            "result": {
                "response": response.answer,
                "status": response.status,
                "metadata": response.metadata,
                # Extract additional fields from metadata if available
                "nutritionData": response.metadata.get("nutrition_data") if response.metadata else None,
                "dishCandidates": response.metadata.get("dish_candidates") if response.metadata else None,
                "recommendedDishes": response.metadata.get("recommended_dishes") if response.metadata else None,
                "ingredientCandidates": response.metadata.get("ingredient_candidates") if response.metadata else None,
                "analysisType": response.metadata.get("analysis_type") if response.metadata else None
            }
        }

    except Exception as e:
        logger.error(f"❌ Nutrition analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nutri-coach")
async def analyze_nutrition_legacy(
    request: Request,
    session_id: str = Form(...),
    text: Optional[str] = Form(None),
    user_profile: str = Form("general"),
    image: Optional[UploadFile] = File(None)
):
    """영양 분석 API - 텍스트 또는 이미지 분석 (Legacy endpoint for /diet-care/nutri-coach)"""
    context_system = get_context_system(request)
    if not context_system.session_manager.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return await _analyze_nutrition_internal(request, session_id, text, user_profile, image)

@router.post("/diet-log")
async def log_diet():
    """Deprecated endpoint; clients must use the persisted diet-care meals API."""
    raise HTTPException(
        status_code=410,
        detail="이 엔드포인트는 폐기되었습니다. /api/diet-care/meals를 사용하세요.",
    )
