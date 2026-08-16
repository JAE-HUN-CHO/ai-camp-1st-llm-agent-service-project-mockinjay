import json
import logging
from types import SimpleNamespace

from langchain_core.messages import HumanMessage, SystemMessage
from app.db.context_manager import ContextManager
from app.adapters.ollama.client import OllamaClient

logger = logging.getLogger(__name__)

class _ContextLLM:
    """Small async invoke wrapper that keeps context analysis Ollama-only."""

    def __init__(self):
        self.client = OllamaClient()

    async def ainvoke(self, messages):
        response = await self.client.chat.completions.create(
            model="qwen3.6:27b-mlx",
            messages=messages,
            temperature=0,
        )
        return SimpleNamespace(content=response.choices[0].message.content)


class ContextEngineer:
    """
    Context Engineer responsible for analyzing user conversation history,
    extracting context/keywords, and maintaining user state.
    """

    def __init__(self):
        self.db_manager = ContextManager()
        # Using a capable model for summarization and extraction
        self.llm = _ContextLLM()

    async def analyze_and_update_context(self, user_id: str):
        """
        Analyze recent conversation history and update user context.
        Should be called periodically or at the end of a session.
        """
        # 1. Fetch recent history
        history = await self.db_manager.get_recent_conversations(user_id, limit=5)
        if not history:
            return

        # Format history for LLM
        history_text = ""
        for chat in history:
            history_text += f"User: {chat['user_input']}\nAgent ({chat['agent_type']}): {chat['agent_response']}\n---\n"

        # 2. Generate Summary and Keywords
        system_prompt = """You are a Context Engineer AI.
        Your goal is to analyze the conversation history of a user and extract key information to personalize their future interactions.
        
        1. Summarize the user's recent interests and questions in 1-2 sentences.
        2. Extract 3-5 key topics or keywords from the conversation.
        
        Output ONLY a JSON object with the following format:
        {
            "summary": "User is interested in...",
            "keywords": ["keyword1", "keyword2", "keyword3"]
        }
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Conversation History:\n{history_text}")
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            
            # Clean up potential markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content)
            summary = result.get("summary", "")
            keywords = result.get("keywords", [])

            # 3. Save to DB
            await self.db_manager.save_user_context(user_id, summary, keywords)
            logger.info("Updated redacted user context")

        except Exception:
            logger.error("Failed to analyze redacted user context", exc_info=True)

    async def get_user_context(self, user_id: str) -> dict:
        """
        Retrieve the stored context for a user.
        Returns a dict with 'summary' and 'keywords'.
        """
        context = await self.db_manager.get_user_context(user_id)
        if context:
            return {
                "summary": context.get("summary", ""),
                "keywords": context.get("keywords", [])
            }
        return {"summary": "", "keywords": []}
