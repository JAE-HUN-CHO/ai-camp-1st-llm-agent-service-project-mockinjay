
import sys
import asyncio
import logging
from pathlib import Path

# Add backend path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import agents
from Agent.router.agent import RouterAgent
from Agent.core.contracts import AgentRequest

async def test_router_default():
    print("\n" + "="*50)
    print("🚀 Starting Router Default Behavior Test")
    print("="*50 + "\n")

    router = RouterAgent()
    
    # Test Cases for Default Routing
    test_cases = [
        {
            "name": "General Medical Question",
            "query": "감기에 걸렸을 때 좋은 음식은 뭐야?", # This might trigger nutrition too, let's try something more generic
            "expected": ["research_paper", "nutrition"] # Actually this is a good complex case
        },
        {
            "name": "Vague Symptom",
            "query": "머리가 아파요.",
            "expected": ["research_paper"]
        },
        {
            "name": "General Knowledge",
            "query": "인체 해부학에 대해 알려줘.",
            "expected": ["research_paper"]
        },
        {
            "name": "Ambiguous Query",
            "query": "그냥 궁금한게 있어.",
            "expected": ["research_paper"]
        }
    ]

    for case in test_cases:
        logger.info(f"\nTesting Case: {case['name']} - Query: {case['query']}")
        
        request = AgentRequest(
            query=case['query'],
            session_id="test_default",
            context={}
        )
        
        try:
            # We only care about the routing decision here, but process executes it.
            # We can inspect the logs or the metadata in the response.
            response = await router.process(request)
            
            routed_to = response.metadata.get('routed_to', [])
            logger.info(f"Routed To: {routed_to}")
            
            # Check if research_paper is in the routed agents
            if "research_paper" in routed_to:
                print(f"✅ Passed: {case['name']} routed to {routed_to}")
            else:
                print(f"❌ Failed: {case['name']} routed to {routed_to} (Expected research_paper)")

        except Exception as e:
            logger.error(f"❌ Test Failed with Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_router_default())
