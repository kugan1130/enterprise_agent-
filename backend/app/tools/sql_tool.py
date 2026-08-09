"""SQL Query validation, schema inspection, and read-only execution tools wrapped as LangChain Tools."""

import re
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy import inspect, text

from backend.app.core.database import SessionLocal

FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "COPY",
}


def get_database_schema() -> str:
    """Inspects database tables and column definitions dynamically."""
    try:
        with SessionLocal() as session:
            inspector = inspect(session.bind)
            table_names = inspector.get_table_names()
            if not table_names:
                return "Database contains no tables."

            schema_lines = []
            for table in table_names:
                columns = inspector.get_columns(table)
                col_defs = [f"{col['name']} ({col['type']})" for col in columns]
                schema_lines.append(f"Table '{table}': {', '.join(col_defs)}")

            return "\n".join(schema_lines)
    except Exception as err:
        return f"Unable to inspect schema: {str(err)}"


def validate_read_only_sql(query: str) -> str:
    """Validates that a SQL query is a single read-only SELECT or WITH statement."""
    if not query or not isinstance(query, str) or not query.strip():
        raise ValueError("SQL query string cannot be empty.")

    cleaned_query = query.strip()
    if cleaned_query.endswith(";"):
        cleaned_query = cleaned_query[:-1].strip()

    if ";" in cleaned_query:
        raise ValueError("Multiple SQL statements are prohibited.")

    no_comments = re.sub(r"--.*$", "", cleaned_query, flags=re.MULTILINE)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL).strip()

    if not no_comments:
        raise ValueError("Query string contains no executable SQL statement.")

    upper_query = no_comments.upper()

    for keyword in FORBIDDEN_KEYWORDS:
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, upper_query):
            raise ValueError(f"Forbidden SQL modification operation: '{keyword}' is prohibited.")

    if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
        raise ValueError("Only read-only SELECT queries are permitted.")

    return cleaned_query


def execute_sql_query(query: str) -> Dict[str, Any]:
    """Validates and executes a read-only SELECT SQL query against the database engine."""
    try:
        validated_sql = validate_read_only_sql(query)
    except ValueError as val_err:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": str(val_err),
        }

    try:
        with SessionLocal() as session:
            result = session.execute(text(validated_sql))
            if result.returns_rows:
                columns = list(result.keys())
                raw_rows = result.fetchall()
                rows = [
                    dict(
                        zip(
                            columns,
                            [
                                int(v) if isinstance(v, Decimal) and v == v.to_integral_value() else float(v) if isinstance(v, Decimal) else v
                                for v in row
                            ],
                        )
                    )
                    for row in raw_rows
                ]
                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "error": None,
                }
            else:
                return {
                    "success": True,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "error": None,
                }
    except Exception as db_err:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": f"Database error: {str(db_err)}",
        }
