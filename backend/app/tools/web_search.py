import logging
from backend.app.core.config import settings
from langchain_core.tools import tool

logger = logging.getLogger("enterprise_ai.web_search")


@tool
def search_web(query: str) -> str:
    """Search the live web for real-time external information and news.

    Returns a formatted string of results, or a clear error/unavailability message.
    Never fabricates results — if search cannot be performed, returns an explicit message.
    """
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        msg = "Web search is disabled: TAVILY_API_KEY is not set."
        logger.warning(msg)
        return msg

    try:
        from tavily import TavilyClient
        response = TavilyClient(api_key=api_key).search(
            query=query,
            search_depth="basic",
            max_results=5,
        )
        results = response.get("results", [])
        if not results:
            return "No web search results found for this query."

        formatted = "\n\n".join(
            f"{i}. {r['title']}\n{r['content']}\nSource: {r['url']}"
            for i, r in enumerate(results, start=1)
        )
        logger.info("Web search succeeded for query %r — %d results", query, len(results))
        return formatted

    except Exception as err:
        logger.warning("Web search error for query %r: %s", query, err)
        return f"Web search unavailable: {str(err)}"
