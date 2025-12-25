import os
import sys
import json
from typing import Dict, Any, Optional, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import get_utility_logger, set_console_logging

class BaseValidateProcess:

    def __init__(
        self,
        course_metadata: Optional[Dict[str, Any]],
        file_path: str,
        generation_type: str,
        logger_name: str = "base_validate_process",
        log_file_name: Optional[str] = None,
        console_logging: bool = False,
        schema: Optional[Any] = None
    ):
        set_console_logging(console_logging)
        self.course_metadata = course_metadata
        self.file_path = file_path
        self.generation_type = generation_type
        self.schema = schema

        # Initialize file I/O controller
        self.file_io = SystemIOController()

        # Initialize logger
        if log_file_name is None:
            log_file_name = f"validate_{generation_type.replace('-', '_')}.log"

        self.logger = get_utility_logger(logger_name, log_file_name)
        self.logger.info(f"Initialized {logger_name} for type: {generation_type}")


    @try_catch
    def check_file_exists(self) -> bool:
        self.logger.info(f"Checking file existence: {self.file_path}")

        if not self.file_path:
            self.logger.error("File path is empty or None")
            return False

        if not os.path.exists(self.file_path):
            self.logger.error(f"File does not exist: {self.file_path}")
            return False

        if not os.path.isfile(self.file_path):
            self.logger.error(f"Path exists but is not a file: {self.file_path}")
            return False

        file_size = os.path.getsize(self.file_path)
        if file_size == 0:
            self.logger.error(f"File is empty: {self.file_path}")
            return False

        self.logger.info(f"File exists and is not empty: {self.file_path} ({file_size} bytes)")
        return True

    @try_catch
    def validate_schema(self) -> bool:
        self.logger.info(f"Validating schema for file: {self.file_path}")
        try:
            file_content = self.file_io.read_json(self.file_path)

            if not file_content:
                self.logger.error("File content is empty or invalid JSON")
                return False

            try:
                validated_data = self.schema(**file_content)
                self.logger.info(f"Schema validation passed")
                self.logger.info(f"Validated data type: {type(validated_data).__name__}")
                return True

            except Exception as e:
                self.logger.error(f"Schema validation failed:")
                self.logger.error(f"  Error: {str(e)}")
                return False

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Error during validation: {str(e)}")
            return False

    @try_catch
    def validate(self) -> bool:
        self.logger.info(f"Starting validation for {self.generation_type}")
        self.logger.info(f"File: {self.file_path}")

        if not self.check_file_exists():
            self.force_logging("File existence check failed")
            return False

        if self.schema:
            if not self.validate_schema():
                self.force_logging("Schema validation failed")
                return False

        return True

    def force_logging(self, message: str) -> None:
        print(f"[{self.logger.name}] {message}")
        self.logger.info(message)
