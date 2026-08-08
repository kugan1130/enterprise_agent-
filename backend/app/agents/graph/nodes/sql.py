"""SQL agent node for the chat workflow."""

import json

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.sql_tool import execute_sql_query


async def sql_node(state: GraphState, llm_client: LLMClient) -> dict[str, str]:
    """
    Generates a read-only SQL query for the user question,
    executes it via sql_tool, and returns the result string in state["sql_result"].
    """
    user_message = state["user_message"]

    sql_prompt = (
        "You are a database analyst. "
        "Generate a single read-only SQL SELECT query to answer the user question.\n"
        "Database schema: Table 'sales' with columns (id, customer_name, region, product, amount, sale_date).\n"
        "Rules:\n"
        "- Return ONLY the raw SQL statement.\n"
        "- Do NOT use markdown syntax or code blocks.\n"
        "- Only generate SELECT queries.\n\n"
        f"User Question: {user_message}"
    )

    raw_sql = await llm_client.generate(sql_prompt)
    clean_sql = raw_sql.replace("```sql", "").replace("```", "").strip()

    # Execute query via existing sql_tool
    result = execute_sql_query(clean_sql)
    return {"sql_result": json.dumps(result)}
