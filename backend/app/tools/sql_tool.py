"""Safe read-only SQL tool and schema inspector for PostgreSQL database."""

import logging
import re
from typing import Any, Dict, List
from sqlalchemy import inspect, text
from backend.app.core.database import SessionLocal, engine

logger = logging.getLogger("enterprise_ai.sql_tool")

FORBIDDEN_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "RENAME", "REPLACE"
}


def get_database_schema() -> str:
    """Inspects PostgreSQL database metadata and returns a readable schema summary with domain hints."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        schema_lines = []
        for table in tables:
            columns = inspector.get_columns(table)
            col_desc = ", ".join(f"{c['name']} ({c['type']})" for c in columns)
            schema_lines.append(f"Table '{table}': {col_desc}")
            
        if "sales" in tables:
            schema_lines.append(
                "\nDomain Knowledge for 'sales' table:\n"
                "- Columns: id (INT), transaction_id (VARCHAR e.g. 'TXN-2026-001'), sale_date (DATE 'YYYY-MM-DD'), "
                "product_name (VARCHAR), product_category (VARCHAR), region (VARCHAR), customer_name (VARCHAR), "
                "quantity (INT), unit_price (NUMERIC), revenue (NUMERIC), payment_status (VARCHAR 'Completed'/'Pending')\n"
                "- Standard Products: NovaAnalytics Suite, NovaCloud Enterprise, NovaSync Hub, NovaData Warehouse, NovaSecurity Shield, NovaAI Assistant Platform\n"
                "- Standard Regions: North America, LATAM, APAC, EMEA\n"
                "- Payment Status values: 'Completed', 'Pending'"
            )
        return "\n".join(schema_lines) if schema_lines else "No tables found."
    except Exception as err:
        logger.error("Error inspecting database schema: %s", err)
        return (
            "Table 'sales': id (INT), transaction_id (VARCHAR), sale_date (DATE), product_name (VARCHAR), product_category (VARCHAR), region (VARCHAR), customer_name (VARCHAR), quantity (INT), unit_price (NUMERIC), revenue (NUMERIC), payment_status (VARCHAR)\n"
            "Table 'document_records': id (INT), user_id (INT), filename (VARCHAR), status (VARCHAR), created_at (TIMESTAMP)\n"
            "Table 'users': id (INT), username (VARCHAR), role (VARCHAR)"
        )


def execute_read_only_sql(sql_query: str) -> Dict[str, Any]:
    """Validates and executes a strictly read-only SQL SELECT query against PostgreSQL."""
    clean_sql = sql_query.strip().rstrip(";")
    
    # Strip multiline comments
    clean_sql_no_comments = re.sub(r"/\*.*?\*/", "", clean_sql, flags=re.DOTALL)
    clean_sql_no_comments = re.sub(r"--.*$", "", clean_sql_no_comments, flags=re.MULTILINE).strip()
    
    # Safety Check 1: Must start with SELECT or WITH
    upper_sql = clean_sql_no_comments.upper()
    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        return {
            "success": False,
            "error": "Read-only security policy violation: Only SELECT queries are permitted.",
            "rows": [],
            "columns": [],
            "row_count": 0,
        }

    # Safety Check 2: Check for forbidden destructive keywords
    tokens = set(re.findall(r"\b[A-Z_]+\b", upper_sql))
    forbidden_found = tokens.intersection(FORBIDDEN_KEYWORDS)
    if forbidden_found:
        return {
            "success": False,
            "error": f"Read-only security policy violation: Forbidden operations detected ({', '.join(forbidden_found)}).",
            "rows": [],
            "columns": [],
            "row_count": 0,
        }

    # Execute read-only query
    try:
        with SessionLocal() as db:
            result = db.execute(text(clean_sql_no_comments))
            columns = list(result.keys()) if result.returns_rows else []
            rows = [dict(zip(columns, row)) for row in result.fetchall()] if result.returns_rows else []
            
            return {
                "success": True,
                "query": clean_sql_no_comments,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "error": None,
            }
    except Exception as err:
        logger.error("SQL execution error: %s", err)
        return {
            "success": False,
            "error": f"Database execution error: {str(err)}",
            "rows": [],
            "columns": [],
            "row_count": 0,
        }


# Aliases for compatibility
execute_sql_query = execute_read_only_sql
execute_sql = execute_read_only_sql
