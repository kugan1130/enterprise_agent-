"""Schema-aware SQL agent node for database queries."""

import json
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.sql_tool import execute_sql_query, get_database_schema


async def sql_node(state: GraphState, llm_client: LLMClient) -> dict[str, str]:
    """Inspects database schema, generates read-only SQL, and executes query."""
    user_message = state.get("user_message", "")
    schema_info = get_database_schema()

    sql_prompt = (
        "You are a PostgreSQL Database Specialist. "
        "Generate a single read-only SQL SELECT query to answer the user question.\n\n"
        f"Real Database Schema:\n{schema_info}\n\n"
        "Rules:\n"
        "- Use ONLY table names and column names that exist in the schema above.\n"
        "- Return ONLY the raw SQL SELECT statement.\n"
        "- Do NOT use markdown blocks (```sql).\n"
        "- Only generate SELECT queries.\n\n"
        f"User Question: {user_message}"
    )

    raw_sql = await llm_client.generate(sql_prompt)
    clean_sql = raw_sql.replace("```sql", "").replace("```", "").strip()

    # Execute query via sql_tool
    result = execute_sql_query(clean_sql)
    return {"sql_result": json.dumps(result)}
