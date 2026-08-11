"""PostgreSQL SQL Agent node enforcing read-only execution policies."""

import json
import logging
from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.app.agents.graph.state import AgentState
from backend.app.core.config import settings
from backend.app.tools.sql_tool import execute_read_only_sql, get_database_schema

logger = logging.getLogger("enterprise_ai.sql_agent")

SQL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert PostgreSQL Database Engineer for Enterprise AI Assistant.\n"
               "Your job is to generate a single valid, optimized PostgreSQL SELECT query to answer questions about company sales, revenue, products, customers, transactions, or document metadata.\n\n"
               "Database Schema:\n{schema}\n\n"
               "Rules:\n"
               "1. Use ONLY valid PostgreSQL SELECT or WITH (CTE) statements.\n"
               "2. For sales/revenue calculations, use appropriate SUM(revenue) or SUM(quantity * unit_price), COUNT(), GROUP BY, and ORDER BY clauses.\n"
               "3. Match column names exactly from the schema (e.g. customer_name, product_name, sale_date, payment_status, unit_price, quantity, revenue, region).\n"
               "4. Use ILIKE for case-insensitive text search (e.g. customer_name ILIKE '%Vortex%').\n"
               "5. Do NOT execute DROP, DELETE, UPDATE, INSERT, ALTER, or TRUNCATE.\n"
               "6. Return ONLY the raw SQL query with no markdown formatting or commentary."),
    ("human", "User Question: {query}")
])


TRANSACTION_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an Enterprise Sales Data Extraction Specialist.\n"
               "Extract the sales transaction parameters from the user request into raw JSON formatted like:\n"
               "{{\n"
               '  "customer": "Customer Name",\n'
               '  "product": "Product Name",\n'
               '  "quantity": 5,\n'
               '  "sale_date": "YYYY-MM-DD",\n'
               '  "payment_status": "Completed"\n'
               "}}\n"
               "Return ONLY raw JSON with no markdown wrapping."),
    ("human", "User Request: {query}")
])


async def sql_node(state: AgentState) -> Dict[str, Any]:
    """Generates and executes safe read-only SQL query or structured sales transaction insertion."""
    query = str(state.get("current_query") or (state["messages"][-1].content if state.get("messages") else ""))
    msg_lower = query.lower()

    # Fast check for explicit write/destructive requests
    if any(k in msg_lower for k in ["delete from", "drop table", "truncate table", "update sales set", "remove all"]):
        result = {
            "success": False,
            "error": "Read-only security policy prevents destructive operations (DELETE, DROP, UPDATE, TRUNCATE).",
            "rows": [],
            "row_count": 0,
        }
        return {"sql_results": [result]}

    # Check if user is asking to add/insert a new sale into the sales database
    add_keywords = ["add", "insert", "record", "save", "create sale", "put"]
    sales_keywords = ["sales table", "sales db", "sales database", "into sales", "to sales", "sales", "databb", "data"]
    is_add_request = (
        any(k in msg_lower for k in ["add this", "insert into", "record this", "add to sales", "save this", "sales table"])
        or (any(ak in msg_lower for ak in add_keywords) and any(sk in msg_lower for sk in sales_keywords))
        or ("bought" in msg_lower and ("add" in msg_lower or "table" in msg_lower or "sales" in msg_lower))
    )

    if is_add_request:
        try:
            from backend.app.services.sales_service import process_sales_transaction
            if settings.GROQ_API_KEY:
                llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=settings.MODEL_NAME, temperature=0.0)
                chain = TRANSACTION_EXTRACTION_PROMPT | llm
                extraction_res = await chain.ainvoke({"query": query})
                raw_json = extraction_res.content if isinstance(extraction_res.content, str) else str(extraction_res.content)
                clean_json = raw_json.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)

                cust = data.get("customer", "Vortex Dynamics")
                prod = data.get("product", "NovaCloud Enterprise")
                qty = int(data.get("quantity", 1))
                p_status = data.get("payment_status", "Completed")
                s_date = data.get("sale_date", "2026-01-10")

                res_txn = process_sales_transaction(
                    customer=cust,
                    product=prod,
                    quantity=qty,
                    payment_status=p_status,
                    sale_date=s_date,
                )
                return {"sql_results": [res_txn]}
        except Exception as err:
            logger.error("Transaction insertion handling error: %s", err)

    if not settings.GROQ_API_KEY:
        return {"sql_results": [{"success": False, "error": "GROQ_API_KEY missing for SQL generation."}]}

    try:
        schema = get_database_schema()
        llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=settings.MODEL_NAME, temperature=0.0)
        chain = SQL_PROMPT | llm
        response = await chain.ainvoke({"schema": schema, "query": query})
        content_str = response.content if isinstance(response.content, str) else (response.content[0].get("text", "") if isinstance(response.content, list) and response.content else str(response.content))
        raw_sql = content_str.replace("```sql", "").replace("```", "").strip()

        logger.info("Generated SQL Query: %s", raw_sql)
        res = execute_read_only_sql(raw_sql)
        return {"sql_results": [res]}

    except Exception as err:
        logger.error("SQL Agent node error: %s", err)
        return {"sql_results": [{"success": False, "error": f"SQL Agent error: {str(err)}"}]}
