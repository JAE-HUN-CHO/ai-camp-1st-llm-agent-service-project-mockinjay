"""
Quiz Agent 통합 테스트
실제 Ollama, Vector DB, MongoDB를 사용한 E2E 테스트
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from Agent.quiz.agent import QuizAgent
from Agent.agent_manager import AgentManager


async def test_quiz_generation():
    """퀴즈 생성 테스트 (RAG 통합)"""
    print("\n" + "="*80)
    print("TEST 1: 퀴즈 생성 (daily_quiz)")
    print("="*80)

    agent_manager = AgentManager()
    session_id = agent_manager.create_user_session("test_user_001")

    context = {
        "action": "generate_quiz",
        "userId": "test_user_001",
        "sessionType": "daily_quiz"
    }

    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input="Generate daily quiz",
        session_id=session_id,
        context=context
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        agent_result = result.get("result", {})
        print(f"📊 Session ID: {agent_result.get('sessionId')}")
        print(f"📝 Total Questions: {agent_result.get('totalQuestions')}")
        print(f"🎯 Session Type: {agent_result.get('sessionType')}")
        print(f"💯 Initial Score: {agent_result.get('score')}")

        current_q = agent_result.get("currentQuestion", {})
        print(f"\n❓ First Question:")
        print(f"   Category: {current_q.get('category')}")
        print(f"   Difficulty: {current_q.get('difficulty')}")
        print(f"   Question: {current_q.get('question')}")

        tokens = result.get("result", {}).get("tokens_used", 0)
        print(f"\n🔢 Tokens Used: {tokens}")

        return agent_result.get("sessionId"), agent_result.get("currentQuestion", {}).get("id")
    else:
        print(f"❌ Error: {result.get('error')}")
        return None, None


async def test_answer_submission(session_id: str, question_id: str):
    """답안 제출 테스트"""
    print("\n" + "="*80)
    print("TEST 2: 답안 제출")
    print("="*80)

    agent_manager = AgentManager()
    temp_session_id = agent_manager.create_user_session("test_user_001")

    # 정답 제출
    context = {
        "action": "submit_answer",
        "sessionId": session_id,
        "userId": "test_user_001",
        "questionId": question_id,
        "userAnswer": True  # O/X 퀴즈
    }

    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input=f"Submit answer for question {question_id}",
        session_id=temp_session_id,
        context=context
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        agent_result = result.get("result", {})
        print(f"✔️ Is Correct: {agent_result.get('isCorrect')}")
        print(f"🎯 Correct Answer: {agent_result.get('correctAnswer')}")
        print(f"💡 Explanation: {agent_result.get('explanation')}")
        print(f"🏆 Points Earned: {agent_result.get('pointsEarned')}")
        print(f"📊 Current Score: {agent_result.get('currentScore')}")
        print(f"🔥 Consecutive Correct: {agent_result.get('consecutiveCorrect')}")

        stats = agent_result.get("questionStats", {})
        print(f"\n📈 Question Stats:")
        print(f"   Total Attempts: {stats.get('totalAttempts')}")
        print(f"   Correct Attempts: {stats.get('correctAttempts')}")
        print(f"   User Choice %: {stats.get('userChoicePercentage')}%")

        next_q = agent_result.get("nextQuestion")
        if next_q:
            print(f"\n➡️ Next Question ID: {next_q.get('id')}")
            return next_q.get("id")
        else:
            print(f"\n✅ Last question completed!")
            return None
    else:
        print(f"❌ Error: {result.get('error')}")
        return None


async def test_session_complete(session_id: str):
    """세션 완료 테스트"""
    print("\n" + "="*80)
    print("TEST 3: 세션 완료")
    print("="*80)

    agent_manager = AgentManager()
    temp_session_id = agent_manager.create_user_session("test_user_001")

    context = {
        "action": "complete_session",
        "sessionId": session_id
    }

    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input=f"Complete session {session_id}",
        session_id=temp_session_id,
        context=context
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        agent_result = result.get("result", {})
        print(f"📊 Total Questions: {agent_result.get('totalQuestions')}")
        print(f"✔️ Correct Answers: {agent_result.get('correctAnswers')}")
        print(f"🏆 Final Score: {agent_result.get('finalScore')}")
        print(f"📈 Accuracy Rate: {agent_result.get('accuracyRate')}%")
        print(f"🔥 Streak: {agent_result.get('streak')}")

        print(f"\n📊 Category Performance:")
        for perf in agent_result.get("categoryPerformance", []):
            print(f"   {perf['category']}: {perf['correct']}/{perf['total']} ({perf['rate']}%)")
    else:
        print(f"❌ Error: {result.get('error')}")


async def test_user_stats():
    """사용자 통계 조회 테스트"""
    print("\n" + "="*80)
    print("TEST 4: 사용자 통계 조회")
    print("="*80)

    agent_manager = AgentManager()
    session_id = agent_manager.create_user_session("test_user_001")

    context = {
        "action": "get_stats",
        "userId": "test_user_001"
    }

    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input="Get stats for test_user_001",
        session_id=session_id,
        context=context
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        agent_result = result.get("result", {})
        print(f"👤 User ID: {agent_result.get('userId')}")
        print(f"📊 Total Sessions: {agent_result.get('totalSessions')}")
        print(f"❓ Total Questions: {agent_result.get('totalQuestions')}")
        print(f"✔️ Correct Answers: {agent_result.get('correctAnswers')}")
        print(f"🏆 Total Score: {agent_result.get('totalScore')}")
        print(f"📈 Accuracy Rate: {agent_result.get('accuracyRate')}%")
        print(f"🔥 Current Streak: {agent_result.get('currentStreak')}")
        print(f"🏅 Best Streak: {agent_result.get('bestStreak')}")
        print(f"⭐ Level: {agent_result.get('level')}")


async def test_quiz_history():
    """퀴즈 이력 조회 테스트"""
    print("\n" + "="*80)
    print("TEST 5: 퀴즈 이력 조회")
    print("="*80)

    agent_manager = AgentManager()
    session_id = agent_manager.create_user_session("test_user_001")

    context = {
        "action": "get_history",
        "userId": "test_user_001",
        "limit": 5,
        "offset": 0
    }

    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input="Get history for test_user_001",
        session_id=session_id,
        context=context
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        agent_result = result.get("result", {})
        sessions = agent_result.get("sessions", [])
        print(f"📚 Total Sessions: {agent_result.get('total')}")
        print(f"📄 Showing: {len(sessions)} sessions")
        print(f"🔄 Has More: {agent_result.get('hasMore')}")

        for i, session in enumerate(sessions, 1):
            print(f"\n   Session {i}:")
            print(f"      Type: {session.get('sessionType')}")
            print(f"      Score: {session.get('finalScore')}")
            print(f"      Accuracy: {session.get('accuracyRate')}%")
            print(f"      Completed: {session.get('completedAt')}")


async def test_level_test():
    """레벨 테스트 생성 및 완료"""
    print("\n" + "="*80)
    print("TEST 6: 레벨 테스트 (난이도 혼합)")
    print("="*80)

    agent_manager = AgentManager()
    session_id = agent_manager.create_user_session("test_user_002")

    context = {
        "action": "generate_quiz",
        "userId": "test_user_002",
        "sessionType": "level_test"
    }

    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input="Generate level test quiz",
        session_id=session_id,
        context=context
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        agent_result = result.get("result", {})
        print(f"📊 Session ID: {agent_result.get('sessionId')}")
        print(f"📝 Total Questions: {agent_result.get('totalQuestions')}")
        print(f"🎯 Session Type: {agent_result.get('sessionType')}")
        print(f"💡 난이도 구성: easy 2개 + medium 2개 + hard 1개")

        current_q = agent_result.get("currentQuestion", {})
        print(f"\n❓ First Question:")
        print(f"   Category: {current_q.get('category')}")
        print(f"   Difficulty: {current_q.get('difficulty')}")
        print(f"   Question: {current_q.get('question')}")


async def test_learning_mission():
    """학습 미션 생성 (특정 카테고리/난이도)"""
    print("\n" + "="*80)
    print("TEST 7: 학습 미션 (nutrition + medium)")
    print("="*80)

    agent_manager = AgentManager()
    session_id = agent_manager.create_user_session("test_user_003")

    context = {
        "action": "generate_quiz",
        "userId": "test_user_003",
        "sessionType": "learning_mission",
        "category": "nutrition",
        "difficulty": "medium"
    }

    result = await agent_manager.route_request(
        agent_type="quiz",
        user_input="Generate learning mission quiz",
        session_id=session_id,
        context=context
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        agent_result = result.get("result", {})
        print(f"📊 Session ID: {agent_result.get('sessionId')}")
        print(f"📝 Total Questions: {agent_result.get('totalQuestions')}")
        print(f"🎯 Session Type: {agent_result.get('sessionType')}")
        print(f"📚 Category: nutrition (영양 관리)")
        print(f"⚙️ Difficulty: medium")

        current_q = agent_result.get("currentQuestion", {})
        print(f"\n❓ First Question:")
        print(f"   Question: {current_q.get('question')}")


async def run_full_quiz_flow():
    """전체 퀴즈 플로우 테스트 (생성 → 답안 5개 → 완료 → 통계)"""
    print("\n" + "🎯"*40)
    print("FULL FLOW TEST: 퀴즈 전체 플로우")
    print("🎯"*40)

    # 1. 퀴즈 생성
    session_id, question_id = await test_quiz_generation()

    if not session_id:
        print("\n❌ 퀴즈 생성 실패, 테스트 중단")
        return

    # 2. 5개 문제 답안 제출
    for i in range(5):
        if not question_id:
            print(f"\n⚠️ 문제 {i+1} 없음")
            break

        question_id = await test_answer_submission(session_id, question_id)
        await asyncio.sleep(0.5)  # API rate limit 방지

    # 3. 세션 완료
    await test_session_complete(session_id)

    # 4. 사용자 통계
    await test_user_stats()

    # 5. 퀴즈 이력
    await test_quiz_history()


async def main():
    """메인 테스트 실행"""
    print("\n" + "🚀"*40)
    print("Quiz Agent 통합 테스트 시작")
    print("🚀"*40)

    # Local model configuration check. The Ollama daemon is an external
    # integration prerequisite and is intentionally not started by tests.
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen3.6:27b-mlx")
    if not ollama_model:
        print("\n❌ ERROR: OLLAMA_MODEL is not configured")
        return

    print(f"✅ Ollama model configured: {ollama_model}")

    try:
        # 전체 플로우 테스트
        await run_full_quiz_flow()

        # 추가 테스트
        await test_level_test()
        await test_learning_mission()

        print("\n" + "🎉"*40)
        print("모든 테스트 완료!")
        print("🎉"*40)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
