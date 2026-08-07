import asyncio
import sys
from pathlib import Path

# Allow this standalone test script to import the project package directly.
project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.agents.graph.workflow import create_workflow
from backend.app.llm.groq_provider import GroqProvider
from backend.app.llm.llm_client import LLMClient


async def main() -> None:
    workflow = create_workflow(LLMClient(GroqProvider()))
    result = await workflow.ainvoke(
        {"user_message": "Explain RAG in one sentence"}
    )
    print(result["final_response"])


asyncio.run(main())
