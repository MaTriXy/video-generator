
import os
from typing import Optional
from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.models.openai import OpenAIResponsesModel

from scripts.logging_config import get_utility_logger
from scripts.utility.config import OPENAI_API_KEY
from scripts.utility.tool_metrics import track_tool_call

logger = get_utility_logger('tools.web_search_agent')

# Configuration from environment
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "true").lower() == "true"
WEB_SEARCH_MODEL = os.getenv("WEB_SEARCH_MODEL", "gpt-4o-mini")
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "10"))


class WebSearchAgent:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required for web search agent")

        if not WEB_SEARCH_ENABLED:
            logger.warning("[WEB_SEARCH_AGENT] Web search is disabled")
            self.agent = None
            return

        try:
            # Lazy import to avoid circular dependency
            from scripts.controllers.prompt.prompt_manager import PromptManager

            # Fetch system prompt from PromptManager
            prompt_manager = PromptManager()
            prompt_data = prompt_manager.fetch_and_build_prompt(
                prompt_name="Tools/web_search_prompt",
                tag="production"
            )
            system_prompt = prompt_data.get('system_prompt') or prompt_data.get('prompt', '')

            logger.info(f"[WEB_SEARCH_AGENT] Fetched system prompt from PromptManager")

            # Create OpenAI model
            model = OpenAIResponsesModel(WEB_SEARCH_MODEL)

            # Create agent with web search enabled
            self.agent = Agent(
                name="web-search-agent",
                model=model,
                builtin_tools=[WebSearchTool()],
                system_prompt=system_prompt
            )

            logger.info(f"[WEB_SEARCH_AGENT] Initialized with model: {WEB_SEARCH_MODEL}")

        except Exception as e:
            logger.error(f"[WEB_SEARCH_AGENT] Failed to initialize: {e}")
            self.agent = None

    @track_tool_call("web_search_agent_run", is_root=False)
    async def run(self, query: str, context: Optional[str] = None, max_results: Optional[int] = None) -> str:
        if not self.agent:
            error_msg = "Web search agent not available (disabled or initialization failed)"
            logger.warning(f"[WEB_SEARCH_AGENT] {error_msg}")
            return f"Error: {error_msg}"

        try:
            # Build search prompt
            search_prompt = f"Search the web for: {query}"

            if context:
                search_prompt += f"\n\nContext: {context}"

            if max_results:
                search_prompt += f"\n\nLimit results to {max_results} most relevant sources."

            # Execute search using async method
            result = await self.agent.run(search_prompt)

            # Extract response
            response_text = result.output if hasattr(result, 'output') else str(result)

            logger.info(f"[WEB_SEARCH_AGENT] Search completed for query: {query[:50]}...")
            return response_text

        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            logger.error(f"[WEB_SEARCH_AGENT] {error_msg}")
            return f"Error: {error_msg}"


# Global instance for easy access (Singleton pattern)
_web_search_agent = None

def get_web_search_agent() -> WebSearchAgent:
    """Get or create the global web search agent instance."""
    global _web_search_agent
    if _web_search_agent is None:
        _web_search_agent = WebSearchAgent()
    return _web_search_agent
