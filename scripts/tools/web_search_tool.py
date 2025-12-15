"""
Web Search Tool

Wrapper function for web search agent that can be used as a Pydantic AI tool.
"""

from typing import Optional
from pydantic_ai import RunContext

from scripts.utility.tool_metrics import track_tool_call
from scripts.logging_config import get_utility_logger
from .web_search_agent import get_web_search_agent

logger = get_utility_logger('tools.web_search_tool')

@track_tool_call("web_search_tool", is_root=False)
async def web_search_tool(ctx: RunContext = None, query: str = "", context: Optional[str] = None, max_results: Optional[int] = None) -> str:
    """
    Web search tool using dedicated web search agent.

    This tool uses LLM model with built-in web search to search the web.

    Args:
        ctx: RunContext from Pydantic AI (optional, for compatibility)
        query: Search query string
        context: Optional context for the search
        max_results: Maximum number of results to return

    Returns:
        str: Search results with summary and sources
    """
    logger.info(f"[WEB_SEARCH_TOOL] Executing web search for: {query}")

    try:
        # Get agent instance and execute search
        agent = get_web_search_agent()
        result = await agent.run(
            query=query,
            context=context if context else None,
            max_results=max_results if max_results else None
        )

        logger.info(f'[WEB_SEARCH_TOOL] Successfully completed web search')
        return result

    except Exception as e:
        error_msg = f"Web search failed for '{query}': {str(e)}"
        logger.error(f"[WEB_SEARCH_TOOL] {error_msg}")
        return f"Error: {error_msg}"
