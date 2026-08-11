import asyncio
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.services.chat_service import ChatService


async def main():
    service = ChatService()
    session_id = "vortex_test_session"
    
    q1 = "List all sales transactions for Vortex Dynamics including their NovaCloud Enterprise purchase on 2026-01-10."
    print(f"User Query: {q1}\n")
    res1 = await service.ask(q1, session_id=session_id)
    print("--- ASSISTANT RESPONSE ---")
    print(res1)
    print("--------------------------\n")

    q2 = "What is the total revenue from Vortex Dynamics across all their completed purchases?"
    print(f"User Follow-up Query: {q2}\n")
    res2 = await service.ask(q2, session_id=session_id)
    print("--- ASSISTANT RESPONSE (WITH CONTEXT) ---")
    print(res2)
    print("-----------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())
