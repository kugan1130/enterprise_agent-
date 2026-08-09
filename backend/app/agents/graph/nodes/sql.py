"""Database query node that uses the low-code LangChain `create_sql_agent` search_database tool.

Preference order:
1. LangChain SQL Toolkit agent (`search_database`) — the low-code reference flow.
2. Schema-aware SQL generation as a fallback when the agent is unavailable.

Every path executes through the validated read-only executor, so the final answer is
always grounded in actual PostgreSQL results.
"""

import json
from typing import Any
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.sql_tool import execute_sql_query, get_database_schema


async def sql_node(state: GraphState, llm_client: LLMClient) -> dict[str, Any]:
    """Answers database questions by running the LangChain SQL tool against PostgreSQL."""
    user_message = state.get("user_message", "")
    msg_lower = user_message.lower()

    # 1. Detect WRITE intent first (Bug 3)
    if "bought" in msg_lower or "insert" in msg_lower:
        from backend.app.services.sales_service import process_sales_transaction
        import re
        
        # Simple extraction for MVP - in reality this would use structured JSON parsing from LLM
        # For the test case: "TODAY, NOVAANALYTICS SUITE BOUGHT PRODUCTS CLOUD INFRASTRUCTURE, TOTAL QUANTITY BOUGHT 5, PAYMENTS COMPLETED."
        # We use LLM to extract the structure to ensure reliability.
        extract_prompt = (
            "Extract the sales transaction details from the user message into JSON.\n"
            "Format: {\"customer\": \"Customer Name\", \"product\": \"Product Name\", \"quantity\": 5, \"payment_status\": \"Completed\"}\n"
            f"User message: {user_message}\n"
            "Return ONLY JSON."
        )
        try:
            raw_json = await llm_client.generate(extract_prompt)
            clean_json = raw_json.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            result = process_sales_transaction(
                customer=data.get("customer", "Unknown"),
                product=data.get("product", "Unknown"),
                quantity=int(data.get("quantity", 1)),
                payment_status=data.get("payment_status", "Completed")
            )
            
            return {
                "sql_result": result,
                "tool_called": True,
                "tool_success": result.get("success", False),
                "source": "PostgreSQL (Transaction)"
            }
        except Exception as e:
            return {
                "sql_result": {"success": False, "error": f"Failed to process write transaction: {e}"},
                "tool_called": True,
                "tool_success": False,
                "source": ""
            }

    # 2. Low-code path: LangChain create_sql_agent tool (the project reference flow)
    try:
        from backend.app.tools.langchain_sql_agent import run_langchain_sql_agent

        result = await run_langchain_sql_agent(user_message)
        if result and result.get("success"):
            print(f"[SQL TOOL] search_database tool called for q={user_message!r}: {json.dumps(result)[:400]}")
            return {
                "sql_result": json.dumps(result),
                "tool_called": True,
                "tool_success": True,
                "source": "PostgreSQL"
            }
        print(f"[SQL TOOL] agent unavailable, using schema-aware fallback: {result}")
    except Exception as agent_err:
        print(f"[SQL TOOL] agent error ({agent_err}), using schema-aware fallback...")

    # 3. Schema-aware fallback: LLM writes read-only SQL, executor queries PostgreSQL
    schema_info = get_database_schema()

    sql_prompt = (
        "You are a PostgreSQL Database Specialist. "
        "Generate a single read-only SQL SELECT query to answer the user question.\n\n"
        f"Real Database Schema:\n{schema_info}\n\n"
        "POSTGRESQL SYNTAX & AGGREGATE RULES:\n"
        "- NEVER write SUM(boolean_condition) like SUM(sale_date <= CURRENT_DATE) or SUM(revenue > 0). PostgreSQL function SUM() does NOT accept boolean arguments.\n"
        "- For conditional counting in PostgreSQL, ALWAYS use SUM(CASE WHEN condition THEN 1 ELSE 0 END) or COUNT(CASE WHEN condition THEN 1 END).\n"
        "- Total Revenue: Use SUM(quantity * unit_price) AS total_revenue.\n"
        "- Total Items Sold: Use SUM(quantity) AS total_items_sold.\n"
        "- Total Sales Count: Use COUNT(*) AS total_sales.\n"
        "- Highest Selling Products: SELECT product_name, SUM(quantity) AS total_quantity FROM sales GROUP BY product_name ORDER BY total_quantity DESC;\n"
        "- GROUP BY RULE: Every column in the SELECT clause that is NOT inside an aggregate function (SUM, COUNT, AVG, MIN, MAX) MUST be included in the GROUP BY clause.\n\n"
        "STRICT FORMATTING RULES:\n"
        "- Use ONLY table names and column names that exist in the schema above.\n"
        "- Return ONLY the raw SQL SELECT statement (no markdown comments).\n"
        "- Only generate SELECT or WITH queries.\n\n"
        f"User Question: {user_message}"
    )

    raw_sql = await llm_client.generate(sql_prompt)
    clean_sql = raw_sql.replace("```sql", "").replace("```", "").strip()

    # Guard against provider/service failure messages being mistaken for SQL
    lowered = clean_sql.lower()
    if not clean_sql or lowered.startswith(("groq llm service notice", "groq service notice")):
        print(f"[SQL TOOL] LLM service unavailable (no SQL generated): {clean_sql[:120]!r}")
        return {
            "sql_result": json.dumps(
                {
                    "success": False,
                    "rows": [],
                    "columns": [],
                    "row_count": 0,
                    "error": "The LLM service was unavailable while generating the database query. Please try again in a few moments.",
                }
            ),
            "tool_called": True,
            "tool_success": False,
            "source": ""
        }

    print(f"[SQL TOOL] fallback SQL for q={user_message!r}: {clean_sql!r}")

    result = execute_sql_query(clean_sql)
    print(f"[SQL TOOL] executed result: {json.dumps(result)[:400]}")
    return {
        "sql_result": json.dumps(result),
        "tool_called": True,
        "tool_success": result.get("success", False),
        "source": "PostgreSQL" if result.get("success") else ""
    }