"""
Test script for Context Engineer
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add backend path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Configure logging under the repository log root.
LOG_DIR = Path(__file__).resolve().parents[3] / "logs" / "legacy"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_filename = str(LOG_DIR / f"context_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import Context System
from app.core.context_system import context_system

async def test_context_engineer():
    print("\n" + "="*50)
    print(f"🚀 Starting Context Engineer Test (Logging to {log_filename})")
    print("="*50 + "\n")

    user_id = "test_context_user_v1"
    session_id = f"test_session_{int(datetime.now().timestamp())}"
    
    # 1. Simulate Conversation History
    logger.info("📝 Simulating conversation history...")
    
    conversations = [
        {
            "user_input": "만성신부전 환자에게 좋은 식단이 뭐야?",
            "agent_response": "만성신부전 환자는 칼륨과 인 섭취를 제한해야 합니다. 저염식을 권장하며, 신선한 채소는 물에 담가 칼륨을 제거한 후 섭취하는 것이 좋습니다.",
            "agent_type": "nutrition"
        },
        {
            "user_input": "서울 강남구에 투석 가능한 병원 알려줘",
            "agent_response": "서울 강남구에는 강남세브란스병원, 삼성서울병원 등이 있으며 투석실을 운영하고 있습니다.",
            "agent_type": "medical_welfare"
        },
        {
            "user_input": "투석 비용은 얼마나 들어?",
            "agent_response": "투석 비용은 건강보험 적용 시 본인부담금이 줄어들며, 산정특례 등록 시 10%만 부담하면 됩니다.",
            "agent_type": "medical_welfare"
        }
    ]

    for chat in conversations:
        await context_system.context_engineer.db_manager.save_conversation(
            user_id, 
            session_id, 
            chat["agent_type"], 
            chat["user_input"], 
            chat["agent_response"]
        )
        logger.info(f"   Saved chat: {chat['user_input'][:20]}...")

    # 2. Trigger Analysis
    logger.info("\n🧠 Triggering Context Analysis...")
    await context_system.context_engineer.analyze_and_update_context(user_id)
    
    # 3. Verify Context
    logger.info("\n🔍 Verifying User Context...")
    context = await context_system.context_engineer.get_user_context(user_id)
    
    logger.info(f"   Summary: {context.get('summary')}")
    logger.info(f"   Keywords: {context.get('keywords')}")
    
    if context.get("summary") and context.get("keywords"):
        print("\n✅ Test Passed: Context generated successfully")
        print(f"   Summary: {context.get('summary')}")
        print(f"   Keywords: {context.get('keywords')}")
    else:
        print("\n❌ Test Failed: Context generation failed")

    print("\n" + "="*50)
    print(f"🏁 Test Complete. Check {log_filename} for details.")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(test_context_engineer())
