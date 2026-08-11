import sys
from pathlib import Path
import asyncio
import time

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from Agent.core.agent_registry import AgentRegistry
from Agent.core.contracts import AgentRequest

# Import agents to ensure they are registered
try:
    from Agent.research_paper.agent import ResearchPaperAgent  # noqa: F401
    from Agent.medical_welfare.agent import MedicalWelfareAgent  # noqa: F401
except ImportError:
    # If imports fail, try to rely on auto-discovery or check paths
    print("Warning: Could not import agent classes directly. Relying on Registry.")

async def test_agent(agent_type, query):
    print("\n" + "="*50)
    print(f"🧪 Testing Agent: {agent_type}")
    print(f"📝 Input Query: {query}")
    print("="*50)
    
    try:
        agent = AgentRegistry.create_agent(agent_type)
        request = AgentRequest(
            query=query,
            session_id=f"test_{agent_type}_{int(time.time())}",
            context={},
            profile="general",
            language="ko"
        )
        
        print("⏳ Processing...")
        start = time.time()
        try:
            # User requested 10 minutes timeout
            response = await asyncio.wait_for(agent.process(request), timeout=600.0)
            duration = time.time() - start
            
            print(f"\n✅ Output received in {duration:.2f}s:")
            print("-" * 50)
            print(response.answer)
            print("-" * 50)
            
            if response.sources:
                print(f"\n📚 Sources ({len(response.sources)}):")
                for src in response.sources[:3]:
                    print(f" - {src.get('title', 'No title')}")
        except asyncio.TimeoutError:
            print("\n❌ Timeout: Agent took longer than 600s (10 minutes)")

                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("🚀 Starting Parlant Agents Test")
    print("Ensure 'run_unified_server.py' is running on port 8800")
    
     # Test Research Paper Agent
    print("\n" + "="*50)
    print("🧪 Testing Research Paper Agent")
    print("="*50)
    await test_agent("research_paper", "What are the latest treatments for CKD stage 3?")
    
    # Test Medical Welfare Agent
    await test_agent(
        "medical_welfare", 
        "CKD 환자가 받을 수 있는 복지 혜택과 서울에 있는 투석 가능한 병원을 알려주세요."
    )

if __name__ == "__main__":
    asyncio.run(main())
