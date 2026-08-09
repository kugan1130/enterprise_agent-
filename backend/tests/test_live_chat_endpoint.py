"""Live verification script testing ChatService execution, LLM call, SQL routing, and Redis key writing directly."""

import asyncio
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.app.core.config import settings
from backend.app.core.memory import get_conversation_history
from backend.app.core.redis import get_redis_client
from backend.app.llm.groq_provider import GroqProvider
from backend.app.llm.llm_client import LLMClient
from backend.services.chat_service import ChatService


async def test_live_chat():
    print("=== LIVE CHAT & REDIS VERIFICATION TEST ===")
    print(f"MODEL        : {settings.MODEL_NAME}")
    print(f"DATABASE_URL : {settings.DATABASE_URL}")
    print(f"REDIS_URL    : {settings.REDIS_URL}")

    provider = GroqProvider()
    llm_client = LLMClient(provider)
    chat_service = ChatService(llm_client)

    test_session = "session_live_debug_1"
    test_prompt = "What is the total sales of the company?"

    print(f"\n[1] Invoking ChatService.ask prompt='{test_prompt}' session_id='{test_session}'...")
    try:
        response = await chat_service.ask(test_prompt, test_session)
        print(f"\nSUCCESS! Response from ChatService:")
        print(f"----------------------------------------")
        print(response)
        print(f"----------------------------------------")
    except Exception as err:
        print(f"\nFAIL: ChatService execution error: {err}")
        import traceback
        traceback.print_exc()

    print("\n[2] Checking Redis key storage...")
    r = get_redis_client()
    if r:
        try:
            keys = r.keys(f"chat_session:{test_session}")
            print(f"Redis keys for session: {keys}")
            history = get_conversation_history(test_session)
            print(f"Retrieved history from Redis: {history}")
        except Exception as err:
            print(f"Redis check error: {err}")
    else:
        print("Redis client is not connected!")


if __name__ == "__main__":
    asyncio.run(test_live_chat())
