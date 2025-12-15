"""
Base Post-Processing Class - Abstract base class for all post-processing operations.

This class provides common functionality for reading Claude CLI outputs,
saving versioned files, and updating the course manifest.
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.controllers.gen_metadata_controller import GenMetadataController
from scripts.controllers.output_controller import OutputController, AssetType
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.logging_config import get_utility_logger, set_console_logging
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig


class BasePostProcess(ABC):
    def __init__(
        self,
        logger_name: str,
        log_file_name: str,
        topic: str,
        asset_type: AssetType = AssetType.SCRIPT,
        console_logging: bool = False
    ):
        set_console_logging(console_logging)

        # Set topic in both config and manifest controller
        ClaudeCliConfig.set_topic(topic)
        self.claude_cli_config = ClaudeCliConfig()

        self.manifest_controller = ManifestController()
        self.manifest_controller.set_topic(topic)

        self.asset_type = asset_type
        self.output_controller = OutputController()
        self.file_io = SystemIOController()
        self.gen_metadata_controller = GenMetadataController(asset_type)

        log_file_dir = Path(self.claude_cli_config.BASE_OUTPUT_PATH) / topic / "logs"
        self.logger = get_utility_logger(logger_name, log_file_name, log_file_dir)
        self.logger.info(f"Initialized {logger_name}")

    @try_catch
    def write_versioned_output(
        self,
        asset_type: Optional[AssetType] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        self.logger.info(f"Writing versioned output for asset type: {asset_type}")
        if asset_type is None:
            asset_type = self.asset_type
        source_file = self.claude_cli_config.get_latest_path(asset_type)
        file_path, version = self.output_controller.save_output(asset_type, source_file)
        self.manifest_controller.update_file(asset_type, file_path, version)
        self.logger.info(f"Manifest updated successfully")
        return file_path, version

    def force_logging(self, message: str) -> None:
        print(f"{message}")
        self.logger.info(message)

    @abstractmethod
    def process(self, *args, **kwargs) -> Tuple[bool, Optional[str]]:
        pass

    def run(self) -> Tuple[bool, Optional[str]]:
        self.gen_metadata_controller.set_metadata({"type":"claude_cli"})
        result = self.process()
        self.gen_metadata_controller.save_metadata()
        return result