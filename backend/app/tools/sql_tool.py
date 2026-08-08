import re
from typing import Any, Dict, List
from sqlalchemy import text

from backend.app.core.database import SessionLocal

# Set of SQL operation keywords that modify state or schema
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


def validate_read_only_sql(query: str) -> str:
    """
    Validates that a SQL query string contains a single read-only SELECT or WITH statement.

    Args:
        query: Raw SQL query string.

    Returns:
        Cleaned, validated SQL string.

    Raises:
        ValueError: If the query is empty, contains forbidden modification commands,
                   or contains multiple SQL statements.
    """
    if not query or not isinstance(query, str) or not query.strip():
        raise ValueError("Query string cannot be empty.")

    cleaned_query = query.strip()

    # Allow a single optional trailing semicolon
    if cleaned_query.endswith(";"):
        cleaned_query = cleaned_query[:-1].strip()

    # Reject multiple SQL statements
    if ";" in cleaned_query:
        raise ValueError("Multiple SQL statements are not allowed in a single query.")

    # Strip single-line (-- ...) and multi-line (/* ... */) comments for validation
    no_comments = re.sub(r"--.*$", "", cleaned_query, flags=re.MULTILINE)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL).strip()

    if not no_comments:
        raise ValueError("Query string contains no executable SQL statement.")

    upper_query = no_comments.upper()

    # Check for forbidden keywords first so explicit operation errors (e.g. INSERT, UPDATE, DROP) are raised
    for keyword in FORBIDDEN_KEYWORDS:
        pattern = r"\b" + keyword + r"\b"
        if re.search(pattern, upper_query):
            raise ValueError(f"Forbidden SQL operation detected: {keyword} is not allowed.")

    # Enforce starting with SELECT or WITH (for CTEs leading to SELECT)
    if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
        raise ValueError("Only read-only SELECT queries are allowed.")

    return cleaned_query


def generate_chart_metadata(columns: List[str], rows: List[Dict[str, Any]]) -> Any:
    """
    Generates structured chart metadata (bar, line, pie) for tabular SQL query results.
    Does not produce chart data for scalar/single row results.
    """
    if not columns or not rows or len(rows) <= 1 or len(columns) < 2:
        return None

    # Identify numeric column for Y axis and string/categorical column for X axis
    x_col = None
    y_col = None

    for col in columns:
        val = rows[0][col]
        if isinstance(val, (int, float)) and y_col is None:
            y_col = col
        elif isinstance(val, (str, datetime)) and x_col is None:
            x_col = col

    if not x_col:
        x_col = columns[0]
    if not y_col:
        y_col = columns[1] if len(columns) > 1 else columns[0]

    # Select chart type
    lower_x = str(x_col).lower()
    if "date" in lower_x or "time" in lower_x or "month" in lower_x or "year" in lower_x:
        chart_type = "line"
    elif len(rows) <= 5:
        chart_type = "pie"
    else:
        chart_type = "bar"

    chart_data = [{"x": str(r.get(x_col, "")), "y": r.get(y_col, 0)} for r in rows]

    return {
        "chart_type": chart_type,
        "x": str(x_col),
        "y": str(y_col),
        "data": chart_data,
    }


def execute_sql_query(query: str) -> Dict[str, Any]:
    """
    Validates and executes a read-only SQL query against PostgreSQL using the existing SessionLocal.
    Generates chart metadata for tabular data.
    """
    try:
        validated_sql = validate_read_only_sql(query)
    except ValueError as val_err:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "chart": None,
            "error": str(val_err),
        }

    try:
        with SessionLocal() as session:
            result = session.execute(text(validated_sql))
            if result.returns_rows:
                columns = list(result.keys())
                raw_rows = result.fetchall()
                rows = [dict(zip(columns, row)) for row in raw_rows]
                chart = generate_chart_metadata(columns, rows)
                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "chart": chart,
                    "error": None,
                }
            else:
                return {
                    "success": True,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "chart": None,
                    "error": None,
                }
    except Exception as db_err:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "chart": None,
            "error": f"Database execution error: {str(db_err)}",
        }
