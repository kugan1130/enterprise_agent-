from backend.app.tools.sql_tool import search_database, execute_sql


async def run_langchain_sql_agent(question: str) -> dict:
    try:
        ans = search_database.invoke({"query": question})
        return {"success": True, "answer": str(ans)}
    except Exception as err:
        return {"success": False, "error": str(err)}