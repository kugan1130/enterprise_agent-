"""Aggregation Node synthesizing multi-agent results and building Chart.js datasets."""

from typing import Any, Dict, List, Optional
from backend.app.agents.graph.state import GraphState


def build_chart_data_if_applicable(sql_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Generates a structured Chart.js dataset if SQL results contain numerical data."""
    if not sql_result or not isinstance(sql_result, dict) or not sql_result.get("success"):
        return None

    rows = sql_result.get("rows", [])
    if not rows or not isinstance(rows, list) or len(rows) < 2:
        return None

    columns = sql_result.get("columns", [])
    if not columns:
        columns = list(rows[0].keys())

    label_col = None
    numeric_col = None

    for col in columns:
        val = rows[0].get(col)
        if isinstance(val, (int, float)) and numeric_col is None:
            numeric_col = col
        elif isinstance(val, str) and label_col is None:
            label_col = col

    if not numeric_col:
        return None

    if not label_col:
        label_col = columns[0]

    labels = [str(r.get(label_col, f"Row {i+1}")) for i, r in enumerate(rows)]
    data = [float(r.get(numeric_col, 0)) for r in rows]

    return {
        "type": "bar",
        "title": f"{numeric_col.replace('_', ' ').title()} by {label_col.replace('_', ' ').title()}",
        "labels": labels,
        "datasets": [
            {
                "label": numeric_col.replace("_", " ").title(),
                "data": data,
                "backgroundColor": "rgba(99, 102, 241, 0.6)",
                "borderColor": "rgba(99, 102, 241, 1)",
                "borderWidth": 1,
            }
        ],
    }


def aggregate_node(state: GraphState) -> Dict[str, Any]:
    """Combines multi-source results and builds chart visualization data."""
    sql_res = state.get("sql_result")
    chart_data = build_chart_data_if_applicable(sql_res)

    sources: List[Dict[str, Any]] = []

    # Document sources
    rag_ctx = state.get("rag_context", "")
    if rag_ctx and "Source Document:" in rag_ctx:
        import re
        matches = re.findall(r"Source Document:\s*([^\s\()]+)", rag_ctx)
        for m in set(matches):
            sources.append({"type": "document", "name": m, "page": 1})

    # Database sources
    if sql_res and isinstance(sql_res, dict) and sql_res.get("success"):
        sources.append({"type": "database", "table": "sales"})

    # Web sources
    web_res = state.get("web_results")
    if web_res and isinstance(web_res, str):
        sources.append({"type": "web", "title": "Web Search Results", "url": "tavily.com"})

    output_state: Dict[str, Any] = {"sources": sources}
    if chart_data:
        output_state["chart_data"] = chart_data

    return output_state
