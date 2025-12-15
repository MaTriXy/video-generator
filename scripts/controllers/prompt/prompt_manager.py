"""
Prompt Manager - Singleton class for managing prompts

This singleton manager integrates PromptCacheController and PromptProcessor
to provide a unified interface for fetching and building prompts.
"""

from math import log
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from threading import Lock

from scripts.controllers.gen_metadata_controller import GenMetadataController
from scripts.controllers.prompt.prompt_cache_controller import PromptCacheController
from scripts.controllers.prompt.prompt_process_controller import PromptProcessController
from scripts.controllers.utils import SingletonMeta
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.utils.session_manager import SessionManager
from scripts.enums import AssetType
from scripts.tools.tools_manager import ToolsManager
from scripts.logging_config import get_utility_logger
from scripts.controllers.utils.system_io_controller import SystemIOController

# Initialize logger
logger = get_utility_logger('controllers.prompt_manager')

class PromptManager(metaclass=SingletonMeta):
    """
    Singleton class for managing prompts.

    This manager provides:
    - Centralized prompt fetching (from cloud or cache)
    - Prompt processing and variable substitution
    - System/user prompt extraction
    - Caching management
    """

    # def get_agent_tool_config(self,agent_name: str):
    #     data=SystemIOController().read_json(f"configs/tools_config.json")
    #     return data.get("agents", {}).get(agent_name, {})



    def __init__(self):
        """Initialize the PromptManager if not already initialized."""
        self._prompt_processor = PromptProcessController()
        self._cache_controller = PromptCacheController()
        self.tools_manager = ToolsManager()
        self.session_manager = SessionManager()

        logger.info("PromptManager singleton instance initialized")

    def check_if_variables_remaining(self, prompt: str, prompt_type: str = "", prompt_name: str = "") -> None:
        if not prompt:
            return

        # Find all variables in {{variable_name}} format
        pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"
        remaining_vars = re.findall(pattern, prompt)

        if remaining_vars:
            context = f" in {prompt_type} prompt" if prompt_type else ""
            name_context = f" for '{prompt_name}'" if prompt_name else ""

            logger.error(f"Unresolved template variables found{context}{name_context}:")
            for var in remaining_vars:
                logger.error(f"  - {{{{ {var} }}}}")

            logger.error("Exiting process due to unresolved template variables")
            sys.exit(1)

    @try_catch
    def old_fetch_and_build_prompt(
        self,
        prompt_name: str,
        variables: Optional[Dict[str, Any]] = None,
        tag: Optional[str] = "production",
        agent_name: str = None,
        lesson_number: Optional[int] = None,
        material_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Fetching and building prompt: {prompt_name}")
        prompt_data = self._cache_controller.fetch_prompt(prompt_name, tag)
        config = prompt_data.get("config", {})
        # tool_config = self.get_agent_tool_config(agent_name)
        # variables['tools'] = tool_config.get("system_prompt", [])
        if not prompt_data:
            logger.error(f"Failed to fetch prompt: {prompt_name}")
            return None, None


        if not prompt_data:
            logger.error(f"Failed to fetch prompt: {prompt_name}")
            return None, None
        
        if "variables" in config:
            variables = {**variables, **config['variables']}
        else:
            variables = variables

        logger.info(f"Processing sub prompts: {prompt_name}")
        processed_prompt_vars = self.process_sub_prompts(prompt_data,lesson_number, material_number, tag, prompt_name)
        system_prompt = None
        user_prompt = None  
        if len(processed_prompt_vars) > 0:
            system_prompt, user_prompt = self._prompt_processor.get_prompt(
                prompt_data["prompt"],
                {**variables, **processed_prompt_vars}
            )
        else:
            system_prompt, user_prompt = self._prompt_processor.get_prompt(
                prompt_data["prompt"],
                variables
            )

        logger.info(f"Successfully built prompt: {prompt_name} ")

        # Validate that no template variables remain in the prompts
        self.check_if_variables_remaining(system_prompt, "system", prompt_name)
        self.check_if_variables_remaining(user_prompt, "user", prompt_name)

        return {
            **prompt_data,
            "system_prompt": system_prompt,
            "prompt": user_prompt,
        }

    
    def process_sub_prompts(self, prompt_data: Dict[str, Any], tag: str="production",prompt_name: str="") -> Dict[str, Any]:
        sub_prompt_vars=self._prompt_processor.parse_sub_prompts(prompt_data['prompt'])
        logger.info(f"injecting sub prompt found in prompt_name: {prompt_name}: {sub_prompt_vars}")
        if len(sub_prompt_vars) > 0:
            sub_prompts = self._prompt_processor.get_sub_prompts(
                prompt_data,
                sub_prompt_vars,
            )
            logger.info(f"selected sub prompts: {json.dumps(sub_prompts, indent=2)}")
            prompt_vars={}
            if len(sub_prompts.items()) > 0:
                for key, value in sub_prompts.items():
                    if value == "":
                        logger.error(f"{key} sub prompt is empty")
                        continue
                    
                    sub_prompt_data=self.fetch_and_build_prompt(
                        prompt_name=value,
                        tag=tag
                    );
                    prompt_vars[f"prompt_{key}"]=(sub_prompt_data["system_prompt"] or "") +" "+sub_prompt_data["prompt"]
            return prompt_vars
        else:
            return {}

            


    @try_catch
    def fetch_and_build_prompt(
        self,
        prompt_name: str,
        variables: Optional[Dict[str, Any]] = {},
        tag: Optional[str] = "production",
        tools: Optional[List[str]] = None,
        agent_name: str = None,
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching and building prompt: {prompt_name}")
        prompt_data = self._cache_controller.fetch_prompt(prompt_name, tag)
        GenMetadataController().set_metadata({prompt_name: prompt_data.get("version", 0)})
        config = prompt_data.get("config", {})
        agent_tools =[]
        tools_prompt = ""
        if "tools" in config and len(config['tools']) > 0:
                tool_names=config['tools']
                if len(tool_names) > 0:
                    tools_data = self.tools_manager.get_tools(tool_names)
                    agent_tools = tools_data['tools']
                    tools_prompt = tools_data['prompts']
                    logger.info(f"Agent tools: {agent_tools}")
        
        if "variables" in config:
            variables = {**variables, **config['variables']}
        else:
            variables = variables
        if not prompt_data:
            logger.error(f"Failed to fetch prompt: {prompt_name}")
            return None, None
        processed_prompt_vars = self.process_sub_prompts(
            prompt_data,
            tag, 
            prompt_name
        )
        system_prompt = None
        user_prompt = None  
        if len(processed_prompt_vars) > 0:
            system_prompt, user_prompt = self._prompt_processor.get_prompt(
                prompt_data["prompt"],
                {**variables, **processed_prompt_vars}
            )
        else:
            system_prompt, user_prompt = self._prompt_processor.get_prompt(
                prompt_data["prompt"],
                variables
            )

        logger.info(f"Successfully built prompt: {prompt_name}")

        # Validate that no template variables remain in the prompts
        self.check_if_variables_remaining(system_prompt, "system", prompt_name)
        self.check_if_variables_remaining(user_prompt, "user", prompt_name)

        return {
            **prompt_data,
            "system_prompt": system_prompt,
            "prompt": user_prompt,
            "tools": agent_tools,
        }
