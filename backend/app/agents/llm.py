import logging
from typing import Any, Dict, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.agents.graph.state import AgentState
from backend.app.services.artifact_service import create_artifact, save_session_artifact

logger = logging.getLogger("enterprise_ai.llm_agent")


async def context_builder_and_llm_node(state: AgentState) -> Dict[str, Any]:
    """Assembles focused context from agent results and history, then synthesizes answer via LCEL chain."""
    session_id = state.get("session_id", "default_session")
    messages_history: List[BaseMessage] = state.get("messages", [])
    user_query = state.get("current_query") or (messages_history[-1].content if messages_history else "")

    rag_results = state.get("rag_results", [])
    web_results = state.get("web_results", [])
    sql_results = state.get("sql_results", [])

    context_blocks: List[str] = []

    if rag_results:
        passages = [f"[Source: {r.get('metadata',{}).get('filename','doc.pdf')}]\n{r.get('text','')}" for r in rag_results if r.get('text')]
        if passages:
            context_blocks.append("--- RETRIEVED DOCUMENTS ---\n" + "\n\n".join(passages))

    if web_results:
        web_text = "\n\n".join(str(w) for w in web_results if w)
        if web_text:
            context_blocks.append("--- RETRIEVED WEB EVIDENCE ---\n" + web_text)

    if sql_results:
        sql_text = "\n\n".join(str(s) for s in sql_results if s)
        if sql_text:
            context_blocks.append("--- RETRIEVED DATABASE EVIDENCE ---\n" + sql_text)

    if context_blocks:
        system_instruction = (
            "You are an Enterprise AI Assistant acting as an expert Database & Knowledge Engineer.\n"
            "Core Instructions:\n"
            "1. Lead with a direct, clear, conversational answer to the user's question.\n"
            "2. Format all structured data, sales transactions, financial figures, or document records into clean Markdown tables.\n"
            "3. Provide a short, bulleted list summarizing key insights or takeaways from the data.\n"
            "4. Copy exact metrics, transaction IDs, product names, dates, unit prices, and revenue totals without modification or fabrication.\n"
            "5. Append transparent source citations for retrieved documents, database queries, or web search results.\n\n"
            f"VERIFIED EVIDENCE:\n" + "\n\n".join(context_blocks)
        )
    else:
        system_instruction = (
            "You are an Enterprise AI Assistant. Answer directly, clearly, and helpfully using prior conversation context.\n"
            "Do NOT fabricate financial/sales/document metrics without verified records."
        )

    # Build LCEL prompt template
    prompt_msgs: List[BaseMessage] = [SystemMessage(content=system_instruction)]
    for msg in messages_history[-8:]:
        if isinstance(msg, (HumanMessage, AIMessage)):
            prompt_msgs.append(msg)
    if not prompt_msgs or not (isinstance(prompt_msgs[-1], HumanMessage) and prompt_msgs[-1].content == user_query):
        prompt_msgs.append(HumanMessage(content=str(user_query)))

    if not settings.GROQ_API_KEY:
        return {"final_response": "I'm sorry, GROQ_API_KEY is not configured."}

    try:
        llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=settings.MODEL_NAME, temperature=0.0)
        chain = llm | StrOutputParser()
        final_text = await chain.ainvoke(prompt_msgs)

        output_state: Dict[str, Any] = {"final_response": final_text}

        if len(final_text) > 40 and context_blocks:
            sources = []
            if rag_results: sources.extend([r.get("metadata", {}).get("filename", "Doc") for r in rag_results])
            if web_results: sources.append("Web Search")
            if sql_results: sources.append("PostgreSQL Database")

            art = create_artifact("text", f"Insight: {str(user_query)[:35]}", final_text, list(set(sources)), "markdown")
            save_session_artifact(session_id, art)
            output_state["artifact"] = art

        return output_state
    except Exception as err:
        logger.error("LLM reasoning error: %s", err)
        return {"final_response": "I'm sorry, an issue occurred generating the response.", "error": str(err)}
