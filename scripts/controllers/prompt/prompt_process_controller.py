import re
import json
from typing import Dict, Any, List, Optional, Tuple

from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import get_utility_logger
from scripts.controllers.manifest_controller import ManifestController

logger = get_utility_logger('prompt_processing')


class PromptProcessController:

    def __init__(self):
        self.manifest_controller = ManifestController()
        logger.info("Initialized PromptProcessor")

    def extract_prompt(self, text: str) -> Optional[List[str]]:
        # Pattern to match sections like: ### SECTION_NAME (params) ###
        pattern = r"###\s*([^#(]+?)\s*\([^)]*?\)\s*###(.*?)(?=###\s*[^#(]+?\s*\([^)]*?\)\s*###|$)"
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            # Extract just the content from each section
            sections = []
            for section_name, section_content in matches:
                sections.append(section_content.strip())
            
            return sections if len(sections) > 0 else None
        else:
            return None

    def build_prompt(
        self,
        variables: Dict[str, Any],
        prompt: str
    ) -> str:
        compiled_prompt = prompt
        for key, value in variables.items():
            escaped_value = str(value).replace('\\', '\\\\')

            pattern1 = r'\{\{' + re.escape(key) + r'\}\}'
            compiled_prompt = re.sub(pattern1, escaped_value, compiled_prompt, flags=re.IGNORECASE)

        logger.debug(f"Built prompt with {variables} variables")
        return compiled_prompt
    
    def get_prompt(
        self,
        prompt: str,
        variables: Optional[Dict[str, Any]] = {}
    ) -> Tuple[Optional[str], Optional[str]]:
        extracted_prompt = self.extract_prompt(prompt)
        system_prompt = None
        user_prompt = None
        if extracted_prompt:
            system_prompt = extracted_prompt[0]
            user_prompt = '\n\n'.join(extracted_prompt[1:] if len(extracted_prompt) > 1 else [])
            system_prompt = self.build_prompt(variables, system_prompt)
            user_prompt = self.build_prompt(variables, user_prompt)
        else:
            user_prompt = self.build_prompt(variables, prompt)
        
        return system_prompt, user_prompt

    def parse_sub_prompts(self,text: str) -> List[str]:
        pattern = r"\{\{prompt_([a-zA-Z_]+)\}\}"
        return re.findall(pattern, text)

    def is_sub_prompt_match(self,selection:Dict[str, Any], sub_prompt_data:Dict[str, Any]) -> bool:
        logger.info(f"Checking if sub prompt matches current item: {selection}, sub prompt data: {sub_prompt_data}")
        selected = True
        data = {**sub_prompt_data}

        if "prompt" in data:
            del data["prompt"]
        if "material" in data:
            del data["material"]
        if "lesson" in data:
            del data["lesson"]

        for key, value in data.items():
            if key not in selection:
                logger.error(f"Sub prompt {sub_prompt_data} does not match selection data {selection}, error {key}")
                raise Exception(f"Sub prompt {sub_prompt_data} does not match selection data {selection}")
            else:
                if(selection[key] != value):
                    selected= False
        logger.info(f"Selected: {selected}")
        return selected

    @try_catch
    def select_sub_prompt(self,selection_data: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for sub_prompt_data in config:
            prompt=sub_prompt_data.get('prompt', '')
            if self.is_sub_prompt_match(selection_data, sub_prompt_data):
               logger.info(f"Selected sub prompt: {prompt}")
               return prompt
        return ""

    @try_catch
    def get_sub_prompts(self, prompt_data: Dict[str, Any], sub_prompts_var: List[str]) -> Dict[str, str]:
        metadata = self.manifest_controller.get_metadata()
        selection_data = {
            "video_ratio": metadata.get("video_ratio"),
            "video_style": metadata.get("video_style"),
        }

        config = prompt_data.get('config', {})
        sub_prompts = {}
        for sub_prompt_var in sub_prompts_var:
            sub_prompt_data = config.get('prompts', {}).get(sub_prompt_var, [])
            logger.info(f"Selecting sub prompt current item: {selection_data}, config from prompt {sub_prompt_var}: {len(config)}")
            sub_prompt = self.select_sub_prompt(selection_data, sub_prompt_data)
            logger.info(f"Sub prompt {sub_prompt_var}: {sub_prompt}")
            sub_prompts[sub_prompt_var]=sub_prompt

        return sub_prompts

    @try_catch
    def inject_sub_prompts(
        self,
        prompt: str,
        sub_prompts: Dict[str, str],
    ) -> Tuple[Optional[str], Optional[str]]:
        logger.info(f"Injecting sub prompts.")