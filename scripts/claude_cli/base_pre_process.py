import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from glob import glob

from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.gen_metadata_controller import GenMetadataController
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.output_controller import OutputController
from scripts.enums import AssetType

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.controllers.prompt.prompt_manager import PromptManager
from scripts.logging_config import get_utility_logger, set_console_logging
from pathlib import Path


class BasePreProcess(ABC):

    def __init__(
        self,
        asset_type: AssetType,
        logger_name: str,
        log_file_name: str,
        topic: str,
        console_logging: bool = False,
        gen_prompt: bool = True,
    ):
        set_console_logging(console_logging)
        self.console_logging = console_logging

        # Set topic in both config and manifest controller
        ClaudeCliConfig.set_topic(topic)
        self.claude_cli_config = ClaudeCliConfig()

        self.manifest_controller = ManifestController()
        self.manifest_controller.set_topic(topic)

        self.asset_type = asset_type
        self.prompt_name = self.claude_cli_config.get_prompt_name(asset_type)
        self.prompt_path = self.claude_cli_config.get_prompt_path(asset_type)
        self.claude_cli_output_path = self.claude_cli_config.get_latest_path(asset_type)
        self.prompt_tag = self.claude_cli_config.get_prompt_tag(asset_type)
        self.gen_prompt = gen_prompt

        # Initialize video system controllers
        self.output_controller = OutputController()
        self.prompt_manager = PromptManager()
        self.gen_metadata_controller = GenMetadataController(asset_type)
        self.file_io = SystemIOController()

        log_file_dir = Path(self.claude_cli_config.BASE_OUTPUT_PATH) / topic / "logs"
        self.logger = get_utility_logger(logger_name, log_file_name, log_file_dir)
        self.logger.info(f"Initialized {logger_name} with video system and prompt: {self.prompt_name}")

    @try_catch
    def build_prompt(
        self,
        variables: Dict[str, Any],
        output_format: Optional[str] = None,
    ) -> str:
        tag = self.prompt_tag
        self.logger.info(f"building prompt{self.prompt_name}")
        prompt_data = self.prompt_manager.fetch_and_build_prompt(
            prompt_name=self.prompt_name,
            variables=variables,
            tag=tag
        )
        # if output_format is None:
        #     output_format = (
        #         f"output_format: {prompt_data['config']['output_schema']}"
        #         if prompt_data['config'].get('output_schema')
        #         else ""
        #     )

        current_date = datetime.now().strftime("%d/%m/%Y")

        system_prompt = prompt_data.get('system_prompt', '')
        user_prompt = prompt_data.get('prompt', '')

        prompt_parts = [system_prompt or "", user_prompt or ""]
        if output_format:
            prompt_parts.append(output_format)
        prompt_parts.append(f"| CURRENT DATE: {current_date}")
        self.gen_metadata_controller.set_metadata({"prompt_tag": tag})
        return "\n".join(prompt_parts)

    @try_catch
    def save_prompt_to_file(self, prompt: str, scene_index: Optional[int] = 0) -> None:
        self.logger.info(f"Saving prompt to: {self.prompt_path}")
        self.file_io.write_text(self.prompt_path.format(scene_index=scene_index), prompt)
        self.logger.info(f"Prompt saved to: {self.prompt_path}")

    @try_catch
    def get_metadata(self) -> Dict[str, Any]:
        metadata = self.manifest_controller.get_metadata()
        if not metadata:
            raise ValueError("No metadata found")
        return metadata

    def force_logging(self, message: str) -> None:
        try:
            print(f"[{self.logger.name}] {message}")
        except UnicodeEncodeError:
            safe_message = message.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
            print(f"[{self.logger.name}] {safe_message}")
        self.logger.info(message)

    @try_catch
    def delete_existing_outputs(self):
        path_template = self.claude_cli_config.get_latest_path(self.asset_type)
        pattern = path_template.format(scene_index='*', asset_name='*')
         # Normalize path for cross-platform compatibility
        pattern = str(Path(pattern))
        matching_files = glob(pattern)

        self.logger.info(f"Pattern: {pattern}, Matching files: {matching_files}")
        if matching_files:
            self.logger.info(f"Found {len(matching_files)} existing files to delete")
            for file_path in matching_files:
                try:
                    self.file_io.delete_file(file_path)
                    self.logger.info(f"Deleted: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete {file_path}: {str(e)}")
        else:
            self.logger.info("No existing files found")


    @try_catch
    def delete_existing_prompts(self):
        path_template = self.claude_cli_config.get_prompt_path(self.asset_type)
        pattern = path_template.format(scene_index='*')
        # Normalize path for cross-platform compatibility
        pattern = str(Path(pattern))
        matching_files = glob(pattern)
        self.logger.info(f"Pattern: {pattern}, Matching files: {matching_files}")
        if matching_files:
            self.logger.info(f"Found {len(matching_files)} existing prompts to delete")
            for file_path in matching_files:
                try:
                    self.file_io.delete_file(file_path)
                    self.logger.info(f"Deleted: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete {file_path}: {str(e)}")
        else:
            self.logger.info("No existing prompts found")

    @abstractmethod
    def build_prompt_variables(self, *args, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def save_prompt(self, *args, **kwargs) -> None:
        pass

    def run(self):
        self.delete_existing_outputs()
        self.delete_existing_prompts()
        self.logger.info(f"Deleted existing outputs for {self.asset_type}")
        if self.gen_prompt:
            self.save_prompt()
            self.logger.info(f"Saved prompts for {self.asset_type}")
        else:
            self.logger.info(f"Skipped saving prompts for {self.asset_type}")
        self.logger.info(f"Completed pre-processing for {self.asset_type}")
        self.gen_metadata_controller.save_metadata()
