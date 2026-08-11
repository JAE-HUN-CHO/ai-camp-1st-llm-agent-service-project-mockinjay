"""
Test script for Router Agent with Detailed Logging
"""

import sys
import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime

# Add backend path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Configure logging under the repository log root.
LOG_DIR = Path(__file__).resolve().parents[3] / "logs" / "legacy"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_filename = str(LOG_DIR / f"router_test_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import agents
from Agent.router.agent import RouterAgent
from Agent.core.contracts import AgentRequest

async def test_router():
    print("\n" + "="*50)
    print(f"🚀 Starting Router Agent Test (Logging to {log_filename})")
    print("="*50 + "\n")

    router = RouterAgent()
    
    # Test Cases
    test_cases = [
        # {
        #     "name": "Complex Intent (Both)",
        #     "query": "나는 일반인이야. 만성신부전(CKD)의 주요 증상은 무엇이며, 서울에 있는 투석 가능한 병원을 찾아줘.",
        # },
        # {
        #     "name": "Research Only",
        #     "query": "나는 일반인이야. CKD 3단계의 특징과 관리 방법에 대해 알려줘.",
        # },
        # {
        #     "name": "Research Only",
        #     "query": "나는 일반인이야. 만성신부전의 최근 주요 연구 결과를 알려줘.",
        # },
        # {
        #     "name": "Welfare Only",
        #     "query": "나는 일반인이야. 서울시 강남구에 있는 신장 장애인 복지 혜택을 알려줘.",
        # }, 
        # {
        #     "name": "Welfare Only",
        #     "query": "나는 일반인이야. 서울시 서초구에 있는 투석 가능한 병원을 찾아줘.",
        # },
        # {
        #     "name": "Nutrition Only",
        #     "query": "만성신부전 환자에게 좋은 저칼륨 식단을 추천해줘.",
        # },
        {
            "name": "Quiz Only",
            "query": "만성신부전에 대한 퀴즈를 풀어보고 싶어.",
        },
        # {
        #     "name": "Trend Visualization Only",
        #     "query": "최근 5년간 만성신부전 연구 트렌드를 그래프로 보여줘.",
        # },
        # {
        #     "name": "Complex (Nutrition + Trend)",
        #     "query": "만성신부전 식이요법에 대한 최신 연구 트렌드를 알려주고, 관련 식단을 추천해줘.",
        # }
    ]

    for case in test_cases:
        logger.info(f"\n{'='*50}\n🧪 Testing Case: {case['name']}\n📝 Query: {case['query']}\n{'='*50}")
        
        request = AgentRequest(
            query=case['query'],
            session_id=f"test_session_{int(datetime.now().timestamp())}",
            context={},
            profile="general",
            language="ko"
        )
        
        try:
            start_time = datetime.now()
            response = await router.process(request)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"✅ Response Received in {duration:.2f}s")
            routed_to = response.metadata.get('routed_to', ['Unknown'])
            is_synthesis = response.metadata.get('synthesis', False)
            logger.info(f"🤖 Routed To: {routed_to}")
            logger.info(f"🔀 Synthesis Mode: {'Yes (Multiple Agents)' if is_synthesis else 'No (Single Agent)'}")
            
            # Log Individual Agent Responses
            individual_responses = response.metadata.get('individual_responses', {})
            if individual_responses:
                logger.info(f"\n{'='*50}")
                logger.info("📋 INDIVIDUAL AGENT RESPONSES")
                logger.info(f"{'='*50}")
                
                for agent_name, agent_answer in individual_responses.items():
                    logger.info(f"\n┌─ Agent: {agent_name.upper()} ─┐")
                    logger.info(f"│")
                    # Split answer into lines for better formatting
                    for line in agent_answer.split('\n'):
                        logger.info(f"│ {line}")
                    logger.info(f"│")
                    logger.info(f"└{'─'*48}┘\n")
            
            # Log Final Response (Synthesized or Direct)
            logger.info(f"\n{'='*50}")
            if is_synthesis:
                logger.info("🎯 FINAL SYNTHESIZED ANSWER")
            else:
                logger.info("🎯 FINAL ANSWER (Direct from Single Agent)")
            logger.info(f"{'='*50}")
            logger.info(f"\n{response.answer}\n")
            logger.info(f"{'='*50}\n")
            
            if response.status == "success":
                print(f"🎉 Test Passed: {case['name']}")
            else:
                print(f"❌ Test Failed: {case['name']}")
                
        except Exception as e:
            logger.error(f"❌ Test Failed with Exception: {e}", exc_info=True)
            
    print("\n" + "="*50)
    print(f"🏁 Test Complete. Check {log_filename} for details.")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(test_router())
