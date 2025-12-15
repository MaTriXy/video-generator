import json
from typing import Any, Dict, Union
from pathlib import Path

import toon

from scripts.logging_config import get_utility_logger
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.controllers.utils.singleton import SingletonMeta


class JsonToToonController(metaclass=SingletonMeta):

    def __init__(self):
        self.logger = get_utility_logger('JsonToToonController')
        self.io_controller = SystemIOController()

    def _convert(self, data: Any) -> str:
        """Core conversion logic from JSON data to TOON string."""
        return toon.encode(data)

    def convert_json_to_toon(self, json_data: Union[Dict, list, Any]) -> str:
        """
        Convert JSON data (dict/list) to TOON format string.

        Args:
            json_data: The JSON data to convert (dict, list, or any JSON-serializable type)

        Returns:
            TOON formatted string
        """
        self.logger.info("Converting JSON data to TOON format")
        toon_string = self._convert(json_data)
        self.logger.info("Successfully converted JSON to TOON")
        return toon_string

    def convert_json_file_to_toon_file(self, json_file_path: str, toon_file_path: str) -> bool:
        """
        Convert a JSON file to a TOON .txt file.

        Args:
            json_file_path: Path to the source JSON file
            toon_file_path: Path to the destination TOON .txt file

        Returns:
            True if conversion was successful, False otherwise
        """
        self.logger.info(f"Converting JSON file {json_file_path} to TOON file {toon_file_path}")

        json_data = self.io_controller.read_json(json_file_path)
        if json_data is None:
            self.logger.error(f"Failed to read JSON file: {json_file_path}")
            return False

        toon_string = self._convert(json_data)

        # Ensure parent directory exists
        parent_dir = Path(toon_file_path).parent
        if not self.io_controller.exists(str(parent_dir)):
            self.io_controller.ensure_directory(str(parent_dir))

        success = self.io_controller.write_text(toon_file_path, toon_string)
        if success:
            self.logger.info(f"Successfully wrote TOON file: {toon_file_path}")
        else:
            self.logger.error(f"Failed to write TOON file: {toon_file_path}")

        return success
