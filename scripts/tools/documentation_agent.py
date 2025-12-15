
import os
from typing import Optional
from pydantic_ai import Agent, Tool, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scripts.logging_config import get_utility_logger
from scripts.utility.config import OPENAI_API_KEY
from scripts.utility.tool_metrics import track_tool_call

logger = get_utility_logger('tools.documentation_agent')

# Configuration from environment
DOCUMENTATION_ENABLED = os.getenv("DOCUMENTATION_ENABLED", "true").lower() == "true"
DOCUMENTATION_MODEL = os.getenv("DOCUMENTATION_MODEL", "gpt-4.1-nano")
DOCUMENTATION_MAX_TOKENS = int(os.getenv("DOCUMENTATION_MAX_TOKENS", "5000"))


class DocumentationAgent:

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required for documentation agent")

        if not DOCUMENTATION_ENABLED:
            logger.warning("[DOCUMENTATION_AGENT] Documentation agent is disabled")
            self.agent = None
            return

        try:
            # Lazy import to avoid circular dependency
            from scripts.controllers.prompt.prompt_manager import PromptManager

            # Fetch system prompt from PromptManager
            prompt_manager = PromptManager()
            prompt_data = prompt_manager.fetch_and_build_prompt(
                prompt_name="Tools/documentation_prompt",
                tag="production"
            )
            system_prompt = prompt_data.get('system_prompt') or prompt_data.get('prompt', '')

            logger.info(f"[DOCUMENTATION_AGENT] Fetched system prompt from PromptManager")

            # Create OpenAI model
            model = OpenAIChatModel(DOCUMENTATION_MODEL)

            # Create agent with custom Context7 tools
            self.agent = Agent(
                name="documentation-agent",
                model=model,
                tools=[
                    Tool(self._resolve_library, name="resolve_library", takes_ctx=True),
                    Tool(self._get_documentation, name="get_documentation", takes_ctx=True)
                ],
                system_prompt=system_prompt
            )

            logger.info(f"[DOCUMENTATION_AGENT] Initialized with model: {DOCUMENTATION_MODEL}")

        except Exception as e:
            logger.error(f"[DOCUMENTATION_AGENT] Failed to initialize: {e}")
            self.agent = None

    @track_tool_call("documentation_resolve_library", is_root=False)
    async def _resolve_library(self, ctx: RunContext, library_name: str) -> str:

        logger.info(f"[DOCUMENTATION_AGENT] Resolving library: {library_name}")

        try:
            context7_params = StdioServerParameters(
                command="npx",
                args=["-y", "@upstash/context7-mcp"],
                env={"npm_config_loglevel": os.environ.get("npm_config_loglevel", "verbose")}
            )

            async with stdio_client(context7_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    result = await session.call_tool(
                        "resolve-library-id",
                        {
                            "libraryName": library_name,
                            "tokens": 2500
                        }
                    )

                    # Extract and format result
                    formatted_result = ""
                    if result and hasattr(result, 'content'):
                        if isinstance(result.content, list) and result.content:
                            content = result.content[0]
                            if hasattr(content, 'text'):
                                formatted_result = content.text
                            else:
                                formatted_result = str(content)
                        else:
                            formatted_result = str(result.content)
                    else:
                        formatted_result = str(result)

                    logger.info(f"[DOCUMENTATION_AGENT] Resolved {library_name}: {formatted_result[:200]}...")
                    return formatted_result

        except Exception as e:
            error_msg = f"Failed to resolve library '{library_name}': {str(e)}"
            logger.error(f"[DOCUMENTATION_AGENT] {error_msg}")
            return f"Error: {error_msg}"

    @track_tool_call("documentation_get_docs", is_root=False)
    async def _get_documentation(self, ctx: RunContext, library_id: str, topic: str = "", tokens: int = 2500) -> str:

        logger.info(f"[DOCUMENTATION_AGENT] Getting docs for {library_id}, topic: {topic}")

        try:
            context7_params = StdioServerParameters(
                command="npx",
                args=["-y", "@upstash/context7-mcp"],
                env={"npm_config_loglevel": os.environ.get("npm_config_loglevel", "verbose")}
            )

            async with stdio_client(context7_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # Prepare arguments
                    args = {
                        "context7CompatibleLibraryID": library_id,
                        "tokens": tokens
                    }
                    if topic:
                        args["topic"] = topic

                    result = await session.call_tool("get-library-docs", args)

                    # Extract text content
                    formatted_result = ""
                    if result and hasattr(result, 'content'):
                        if isinstance(result.content, list) and result.content:
                            content = result.content[0]
                            if hasattr(content, 'text'):
                                formatted_result = content.text
                            else:
                                formatted_result = str(content)
                        else:
                            formatted_result = str(result.content)
                    else:
                        formatted_result = str(result)

                    logger.info(f"[DOCUMENTATION_AGENT] Retrieved {len(formatted_result)} chars of documentation")
                    return formatted_result

        except Exception as e:
            error_msg = f"Failed to get documentation for '{library_id}': {str(e)}"
            logger.error(f"[DOCUMENTATION_AGENT] {error_msg}")
            return f"Error: {error_msg}"

    @track_tool_call("documentation_agent_run", is_root=False)
    async def run(self, query: str, topic: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        if not self.agent:
            error_msg = "Documentation agent not available (disabled or initialization failed)"
            logger.warning(f"[DOCUMENTATION_AGENT] {error_msg}")
            return f"Error: {error_msg}"

        try:
            # Build prompt
            prompt = f"Find and retrieve documentation for: {query}"

            if topic:
                prompt += f"\n\nFocus specifically on: {topic}"

            if max_tokens:
                prompt += f"\n\nRetrieve up to {max_tokens} tokens of documentation."

            # Execute agent
            result = await self.agent.run(prompt)

            # Extract response
            response_text = result.output if hasattr(result, 'output') else str(result)

            logger.info(f"[DOCUMENTATION_AGENT] Documentation fetched for query: {query[:50]}...")
            return response_text

        except Exception as e:
            error_msg = f"Documentation fetch failed: {str(e)}"
            logger.error(f"[DOCUMENTATION_AGENT] {error_msg}")
            return f"Error: {error_msg}"


# Global instance for easy access (Singleton pattern)
_documentation_agent = None

def get_documentation_agent() -> DocumentationAgent:
    """Get or create the global documentation agent instance."""
    global _documentation_agent
    if _documentation_agent is None:
        _documentation_agent = DocumentationAgent()
    return _documentation_agent
