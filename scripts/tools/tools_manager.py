from typing import Dict, Any, List, Optional
from pydantic_ai import Tool

from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.utils.session_manager import SessionManager
from scripts.tools.web_search_tool import web_search_tool
from scripts.tools.documentation_tool import documentation_tool
from scripts.logging_config import get_utility_logger
from scripts.controllers.utils.singleton import SingletonMeta
logger = get_utility_logger('tools.manager')


class ToolsManager(metaclass=SingletonMeta):
    def __init__(self):
        self.tool_instances = self._initialize_tools()

        logger.info(f"[TOOLS_MANAGER] Initialized with {len(self.tool_instances)} tools")

    def _initialize_tools(self) -> Dict[str, Tool]:
        tool_instances = {
            "web_search": Tool(web_search_tool, takes_ctx=True, name="web_search"),
            "get_documentation": Tool(documentation_tool, takes_ctx=True, name="get_documentation")
        }

        logger.info(f"[TOOLS_MANAGER] Initialized {len(tool_instances)} tool instances")
        return tool_instances

    @try_catch
    def get_tool_function(self, tool_name: str) -> Any:
        return self.tool_instances[tool_name].function

    @try_catch
    def get_tools(self, tool_names: List[str]) -> Dict[str, Any]:
        tools = []
        prompts = []
        SessionManager().add_summary("tools",  {"tools":tool_names})

        for tool_name in tool_names:
            logger.info(f"[TOOLS_MANAGER] Getting tool: {tool_name}")
            if tool_name in self.tool_instances:
                tool_instance = self.tool_instances[tool_name]
                tools.append(self.tool_instances[tool_name])
                # prompts.append()
                logger.info(f"[TOOLS_MANAGER] Added tool: {tool_name}")
            else:
                logger.warning(f"[TOOLS_MANAGER] Unknown tool requested: {tool_name}")
        logger.info(f"[TOOLS_MANAGER] Returning {len(prompts)} prompts for agent")
        return {'tools': tools, 'prompts': prompts}