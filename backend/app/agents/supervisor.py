import logging
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.agents.graph.state import AgentState

logger = logging.getLogger("enterprise_ai.supervisor")


class RouteDecision(BaseModel):
    """Structured routing decision output."""
    routes: List[Literal["conversation", "rag", "web", "sql"]] = Field(
        description="Capabilities needed: 'conversation', 'rag', 'web', 'sql', or combined ['rag', 'web']."
    )
    reason: str = Field(description="One sentence rationale.")


SUPERVISOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are the Supervisor Agent of an Enterprise AI Assistant.\n"
               "Classify requests strictly into standard capability routes:\n\n"
               "ROUTING RULES:\n"
               "1. 'conversation': Simple greetings ('hi', 'hello', 'hey'), or general conceptual questions without company/web context (e.g. 'Explain what LangGraph is').\n"
               "2. 'rag': Questions about internal enterprise documents, company policies, uploaded resumes, employees, or specific document details (e.g. 'what is our company remote work policy?', 'who is Kanishka?', 'how many innovation days does the experimental team receive?').\n"
               "3. 'web': Questions asking for live internet facts, external news, real-world updates, or public/political figures (e.g. 'who is the CM of Tamil Nadu?', 'what are the latest AI trends?').\n"
               "4. 'sql': Database questions regarding company sales, revenue, product sales counts, top customers, customer lists, transactions, or multi-step sales aggregations (e.g. 'how many products has our company sold?', 'what is the total revenue?', 'which customer bought the highest number of products?', 'list all customers who bought our products').\n"
               "5. Combined ['rag', 'web']: Questions requiring comparing or analyzing internal user documents/resumes alongside current real-world job trends or external facts (e.g. 'Compare my resume with current Agentic AI jobs').\n\n"
               "Output MUST strictly follow RouteDecision structured schema."),
    ("human", "User Request: {query}")
])


async def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """Classifies user request into structured capability routes via LCEL chain."""
    query = str(state.get("current_query") or (state["messages"][-1].content if state.get("messages") else "")).strip()

    greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "thanks", "thank you", "bye", "goodbye"}
    if query.lower().strip("!.,?") in greetings:
        return {"routes": ["conversation"]}

    if not settings.GROQ_API_KEY:
        return {"routes": ["conversation"]}

    try:
        llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=settings.MODEL_NAME, temperature=0.0)
        chain = SUPERVISOR_PROMPT | llm.with_structured_output(RouteDecision)
        res = await chain.ainvoke({"query": query})
        
        if isinstance(res, RouteDecision):
            routes = list(res.routes)
            reason = res.reason
        elif isinstance(res, dict):
            routes = res.get("routes", ["conversation"])
            reason = res.get("reason", "")
        else:
            routes = ["conversation"]
            reason = ""

        logger.info("Supervisor LCEL Route: %s (%s)", routes, reason)
        return {"routes": routes or ["conversation"]}
    except Exception as err:
        logger.error("Supervisor routing error: %s", err)
        return {"routes": ["conversation"]}
