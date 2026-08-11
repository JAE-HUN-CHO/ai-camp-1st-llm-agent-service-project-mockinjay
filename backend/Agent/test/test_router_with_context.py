"""
Test script for Router Agent integrated with Context Engineer
Simulates a user journey and verifies context generation.
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
log_filename = str(LOG_DIR / f"router_context_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import agents and systems
from Agent.router.agent import RouterAgent
from Agent.core.contracts import AgentRequest
from app.core.context_system import context_system

async def test_router_with_context():
    print("\n" + "="*60)
    print("🚀 Starting Router + Context Integration Test")
    print(f"📄 Logging to {log_filename}")
    print("="*60 + "\n")

    # 1. Initialize
    router = RouterAgent()
    user_id = "test_user_journey_v1"
    session_id = f"session_{int(datetime.now().timestamp())}"
    
    # Define a user journey (sequence of queries)
    journey_steps = [
        {
            "name": "Nutrition (Diet)",
            "query": "만성신부전 환자에게 좋은 저칼륨 식단을 추천해줘."
        },
        {
            "name": "Welfare (Support)",
            "query": "서울시 강남구에서 받을 수 있는 신장 장애인 복지 혜택을 알려줘."
        },

        {
            "name": "Hospital (Search)",
            "query": "강남구 근처에 야간 투석이 가능한 병원이 있어?"
        },
        {
            "name": "Research (Condition)",
            "query": "나는 일반인이야. 만성신부전(CKD) 3단계의 주요 증상과 관리 방법이 궁금해."
        },
        {
            "name": "Research (Condition)",
            "query": "나는 연구원이야. 인공지능 관련 만성신부전 연구에 대해 알려줘."
        },
    ]

    print(f"👤 User ID: {user_id}")
    print(f"🆔 Session ID: {session_id}")
    print(f"📅 Steps: {len(journey_steps)}")
    print("-" * 60)

    # 2. Execute Journey (Sequential Processing)
    print("\n🔄 Executing journey steps sequentially...\n")
    
    for idx, step in enumerate(journey_steps, 1):
        print(f"\n{'='*60}")
        print(f"📍 Step {idx}/{len(journey_steps)}: {step['name']}")
        print(f"{'='*60}")
        
        logger.info(f"\n🔹 Step {idx}/{len(journey_steps)}: {step['name']}")
        logger.info(f"❓ Query: {step['query']}")
        
        # 2.1 Get User Context
        logger.info("🧠 Fetching user context...")
        user_context = await context_system.context_engineer.get_user_context(user_id)
        
        context_data = {}
        if user_context:
            context_data['user_history'] = user_context
            logger.info(f"✅ Context found: {len(str(user_context))} chars")
        else:
            logger.info("ℹ️ No previous context found (first turn)")

        # Create Request
        request = AgentRequest(
            query=step['query'],
            session_id=session_id,
            context=context_data,
            profile="general",
            language="ko"
        )

        try:
            # Process with Router (wait for completion)
            print("⏳ Processing query...")
            start_time = datetime.now()
            response = await router.process(request)
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Completed in {duration:.2f}s")
            print(f"🤖 Agent: {response.agent_type}")
            print(f"💬 Answer preview: {response.answer[:100]}...")
            
            logger.info(f"✅ Response ({duration:.2f}s):")
            logger.info(f"   Agent: {response.agent_type}")
            logger.info(f"   Answer: {response.answer[:100]}...") # Log first 100 chars

            # Save to Context History
            print("💾 Saving to conversation history...")
            await context_system.context_engineer.db_manager.save_conversation(
                user_id,
                session_id,
                response.agent_type,
                step['query'],
                response.answer
            )
            logger.info("💾 Saved to conversation history")
            print("✓ Saved successfully")
            
            # Trigger Context Analysis immediately for next step
            print("🧠 Updating context for next step...")
            await context_system.context_engineer.analyze_and_update_context(user_id)
            print("✓ Context updated")
            
            # Wait before next step to ensure sequential processing
            if idx < len(journey_steps):
                print("\n⏸️  Waiting 1 second before next step...")
                await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Step failed: {e}")
            logger.error(f"❌ Step failed: {e}", exc_info=True)
            # Continue to next step even if this one fails
            if idx < len(journey_steps):
                await asyncio.sleep(1)

    # 3. Trigger Context Analysis
    logger.info("\n" + "="*60)
    logger.info("🧠 Triggering Context Analysis...")
    logger.info("="*60)
    
    await context_system.context_engineer.analyze_and_update_context(user_id)
    
    # 4. Verify Result
    logger.info("\n🔍 Verifying User Context...")
    context = await context_system.context_engineer.get_user_context(user_id)
    
    print("\n" + "="*60)
    print("📊 GENERATED USER CONTEXT")
    print("="*60)
    
    if context:
        print(f"\n📝 Summary:\n{context.get('summary')}")
        print(f"\n🔑 Keywords:\n{context.get('keywords')}")
        print(f"\n⏰ Last Updated:\n{context.get('last_updated')}")
        
        if context.get("summary") and context.get("keywords"):
            print("\n✅ TEST PASSED: Context successfully generated from router interactions.")
        else:
            print("\n⚠️ TEST WARNING: Context entry exists but fields are empty.")
    else:
        print("\n❌ TEST FAILED: No context found for user.")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_router_with_context())
