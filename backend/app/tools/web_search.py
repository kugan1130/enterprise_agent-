"""Tavily web search tool wrapped as a standard LangChain Tool."""

import logging
from backend.app.core.config import settings

logger = logging.getLogger("enterprise_ai.web_search")


def search_web(query: str) -> str:
    """Search the live web for real-time external information and news."""
    if not settings.TAVILY_API_KEY:
        return "Web search is disabled: TAVILY_API_KEY is not set."

    try:
        from tavily import TavilyClient
        response = TavilyClient(api_key=settings.TAVILY_API_KEY).search(
            query=query,
            search_depth="basic",
            max_results=5,
        )
        results = response.get("results", [])
        if not results:
            return "No web search results found."

        return "\n\n".join(
            f"{index}. {result['title']}\n{result['content']}\nSource: {result['url']}"
            for index, result in enumerate(results, start=1)
        )
    except Exception as err:
        logger.warning("Web search notice for query %r: %s", query, err)
        return f"Web search error: {str(err)}"
