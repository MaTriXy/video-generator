"""
Documentation Tool

Wrapper function for documentation agent that can be used as a Pydantic AI tool.
"""

from typing import Optional
from pydantic_ai import RunContext

from scripts.utility.tool_metrics import track_tool_call
from scripts.logging_config import get_utility_logger
from .documentation_agent import get_documentation_agent

logger = get_utility_logger('tools.documentation_tool')

@track_tool_call("documentation_tool", is_root=False)
async def documentation_tool(ctx: RunContext = None, query: str = "", topic: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
    logger.info(f"[DOCUMENTATION_TOOL] Fetching documentation for: {query}")

    try:
        # Get agent instance and execute documentation fetch
        agent = get_documentation_agent()
        result = await agent.run(
            query=query,
            topic=topic if topic else None,
            max_tokens=max_tokens if max_tokens else None
        )

        logger.info(f'[DOCUMENTATION_TOOL] Successfully fetched documentation for: {query}')
        return result

    except Exception as e:
        error_msg = f"Documentation fetch failed for '{query}': {str(e)}"
        logger.error(f"[DOCUMENTATION_TOOL] {error_msg}")
        return f"Error: {error_msg}"
