"""Tavily-backed web search for graph nodes."""

from tavily import TavilyClient

from backend.app.core.config import settings


def search_web(query: str) -> str:
    """Search the web and return concise, source-linked results."""
    if not settings.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not configured.")

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
