"""Declarative LangChain & MCP Tool Registry for Enterprise AI Assistant."""

from langchain_core.tools import tool

from backend.app.rag.retriever import retrieve
from backend.app.tools.pdf_report_tool import create_pdf_report
from backend.app.tools.sql_tool import execute_sql_query, get_database_schema
from backend.app.tools.web_search import search_web

sql_schema_tool = tool("get_database_schema_tool")(get_database_schema)
sql_execute_tool = tool("execute_read_only_sql_tool")(execute_sql_query)
pdf_tool = tool("generate_pdf_report_tool")(create_pdf_report)
web_search_tool = tool("web_search_tool")(search_web)
retrieve_tool = tool("retrieve_enterprise_documents_tool")(retrieve)

# Declarative Registry of all standard LangChain Tools
ENTERPRISE_TOOLS = [
    web_search_tool,
    sql_schema_tool,
    sql_execute_tool,
    pdf_tool,
    retrieve_tool,
]

__all__ = [
    "ENTERPRISE_TOOLS",
    "web_search_tool",
    "sql_schema_tool",
    "sql_execute_tool",
    "pdf_tool",
    "retrieve_tool",
]
