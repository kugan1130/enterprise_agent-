import asyncio
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parents[2]
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.services.chat_service import ChatService


async def main():
    service = ChatService()
    session_id = "user_add_sale_session"
    
    prompt = "the Vortex Dynamics company bought 7 no.of NovaCloud Enterprise product on 10.1.2026 and also they paid sucessfully now add this databb into the sales table and also calucalte the total price by using each price ok"
    print(f"User Request: {prompt}\n")
    
    response = await service.ask(prompt, session_id=session_id)
    print("--- ASSISTANT RESPONSE ---")
    print(response)
    print("--------------------------")


if __name__ == "__main__":
    asyncio.run(main())
