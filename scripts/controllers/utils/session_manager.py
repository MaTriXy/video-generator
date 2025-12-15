import json
from typing import Any, Dict
from scripts.controllers.utils.singleton import SingletonMeta
from scripts.logging_config import get_utility_logger

logger = get_utility_logger('session_manager')
class SessionManager(metaclass=SingletonMeta):
    material_number = None
    lesson_number = None
    mode = None
    run_summary = {}


    def add_summary(self, key: str, value: Dict[str, Any]):
            logger.info(f"Adding summary: {key}: {json.dumps(value, indent=2)}")
            if key in self.run_summary:
                self.run_summary[key]={**self.run_summary[key], **value}
            else:
                self.run_summary[key] = value

    def log_summary(self):
        logger.info(f"\n\n{json.dumps(self.run_summary, indent=2)}\n\n")