"""LangChain SQL Toolkit integration exposed as a low-code `search_database` tool.

Uses the official LangChain `create_sql_agent` flow directly (see project reference):
    SQLDatabase -> create_sql_agent(llm, db) -> agent.run(question)

Safety is preserved by wrapping the database executor with a read-only validator so the
agent can never run destructive SQL against the enterprise PostgreSQL database.
"""

import asyncio
import json
from typing import Any, Dict, List

from langchain_core.tools import tool
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.tools.sql_tool import validate_read_only_sql, execute_sql_query

_sql_database_instance = None
_sql_agent_instance = None


class ReadOnlySQLDatabase(SQLDatabase):
    """SQLDatabase that routes every query through the validated read-only executor."""

    def run(self, command: str, fetch: str = "all", include_columns: bool = False):
        validated = validate_read_only_sql(command)
        result = execute_sql_query(validated)
        if not result["success"]:
            raise ValueError(f"Query rejected or failed: {result.get('error')}")
        rows = result["rows"]
        if fetch in ("one", "single") and rows:
            return rows[0]
        if include_columns:
            return result["columns"], rows
        return _render_rows(rows)


def _render_rows(rows: List[Dict[str, Any]]) -> str:
    """Renders structured rows as a compact Markdown table for the agent."""
    if not rows:
        return "No results."
    columns = list(rows[0].keys())
    header = "| " + " | ".join(str(col) for col in columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    body_lines = []
    for row in rows:
        body_lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join([header, separator, *body_lines])


def get_langchain_sql_db() -> SQLDatabase:
    """Returns a read-only LangChain SQLDatabase wrapper over the application engine."""
    global _sql_database_instance
    if _sql_database_instance is None:
        _sql_database_instance = ReadOnlySQLDatabase(engine)
    return _sql_database_instance


def get_sql_agent() -> Any:
    """Builds the create_sql_agent executor exactly like the project's reference pattern."""
    global _sql_agent_instance
    if _sql_agent_instance is None:
        llm = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.MODEL_NAME,
            temperature=0,
        )
        _sql_agent_instance = create_sql_agent(
            llm=llm,
            db=get_langchain_sql_db(),
            verbose=True,
            agent_type="zero-shot-react-description",
            handle_parsing_errors=True,
        )
    return _sql_agent_instance


@tool
def search_database(question: str) -> str:
    """
    Searches the enterprise PostgreSQL database to answer structured/sales questions.
    Act as a database engineer:
    1. Analyze the natural-language question and identify the required aggregation
       (COUNT, SUM, AVG, GROUP BY, ordering, LIMIT).
    2. Generate and execute a precise, read-only SELECT query against the `sales`
       table using the columns: transaction_id, sale_date, product_name,
       product_category, region, customer_name, quantity, unit_price, revenue,
       payment_status.
    3. For revenue totals use SUM(quantity * unit_price) AS total_revenue.
    4. Retry automatically if the query errors. Only SELECT/WITH queries are allowed.
    """
    return run_sql_agent_sync(question)


def run_sql_agent_sync(question: str) -> str:
    """Synchronous wrapper that runs the create_sql_agent and returns its output."""
    agent = get_sql_agent()
    prompt = (
        f"Write and execute a single read-only SQL SELECT query to answer: '{question}'. "
        "For PostgreSQL revenue calculation, use SUM(quantity * unit_price) AS total_revenue. "
        "Return the answer directly with the exact value obtained from the database."
    )
    result = agent.invoke(prompt)
    if isinstance(result, dict):
        return result.get("output") or str(result.get("output", ""))
    return str(result)


async def run_langchain_sql_agent(question: str) -> Dict[str, Any]:
    """
    Runs the create_sql_agent flow on a question and returns a structured result.

    The agent output is produced from an actual PostgreSQL query executed through
    `ReadOnlySQLDatabase`, so the numbers are database-grounded. On any failure the
    call returns `success: False` instead of an invented value.
    """
    try:
        output = await asyncio.to_thread(run_sql_agent_sync, question)
        text = output if isinstance(output, str) else str(output)
        return {"success": True, "answer": text.strip()}
    except Exception as err:
        return {"success": False, "error": f"SQL agent unavailable: {err}"}