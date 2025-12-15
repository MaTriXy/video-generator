import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.enums import AssetType
from scripts.logging_config import get_utility_logger, set_console_logging
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.controllers.utils.singleton import SingletonMeta
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.utility.config import MANIFEST_FILE

class ManifestController(metaclass=SingletonMeta):
    def __init__(self):
        self.current_gen_version = None
        self.logger = get_utility_logger('ManifestController')
        self.io_controller = SystemIOController()
        self.TOPIC = None
        self.manifest_path = "Outputs/{topic}/manifest.json"

    def set_topic(self, topic: str) -> None:
        self.TOPIC = topic
        self.manifest_path = MANIFEST_FILE.format(topic=topic)
        self._ensure_manifest_exists()
        self.manifest_json = self.io_controller.read_json(self.manifest_path)
        

    def set_dimensions(self) -> None:
        video_ratio = self.manifest_json['metadata']['video_ratio']
        viewport_width = 1080
        viewport_height = 1920
        if(video_ratio == "landscape"):
            viewport_width = 1920
            viewport_height = 1080
        
        self.manifest_json['metadata']['viewport_width'] = viewport_width
        self.manifest_json['metadata']['viewport_height'] = viewport_height
        self.io_controller.write_json(self.manifest_path, self.manifest_json)

    def _ensure_manifest_exists(self) -> None:

        if not os.path.exists(self.manifest_path):
            self.logger.info(f"Manifest not found at {self.manifest_path}, creating new one")

            # Ensure the Outputs directory exists
            os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)

            initial_manifest = {
                "metadata": {
                    "video_ratio": "portrait",
                    "video_style": "what-if"
                },
                "Research": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0
                },
                "Scripts": {
                    "version": 1,
                    "path": f"Outputs/{self.TOPIC}/Scripts/script-v1.md",
                    "current_gen_version": 1
                },
                "Audio": {
                    "version": 0,
                    "path": None,
                    "transcript_path": None,
                    "current_gen_version": 0
                },
                "Direction": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0
                },
                "Assets": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0
                },
                "Design": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0
                },
                "Video": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0
                },
                "Transcript": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0
                }
            }

            self.io_controller.write_json(self.manifest_path, initial_manifest)
            self.logger.info("Created new manifest.json with initial null values")

    def get_metadata(self) -> Dict[str, Any]:
        try:
            self.set_dimensions()
            return self.manifest_json['metadata']
        except Exception as e:
            self.logger.error(f"Failed to get metadata: {str(e)}")
            return None

    def get_field(self, asset_type: AssetType, default: Any = None) -> Any:
        return self.manifest_json[asset_type.value] or default

    def get_current_gen_version(self, asset_type: AssetType) -> Optional[int]:
        if(self.current_gen_version is None):
            version = self.manifest_json[asset_type.value].get('version') or 0
            if "current_gen_version" not in self.manifest_json[asset_type.value]  or self.manifest_json[asset_type.value]['current_gen_version'] == self.manifest_json[asset_type.value]['version']:
                self.manifest_json[asset_type.value]['current_gen_version'] = version + 1
            self.io_controller.write_json(self.manifest_path, self.manifest_json)
            self.current_gen_version = self.manifest_json[asset_type.value]['current_gen_version']

        return self.current_gen_version

    @try_catch
    def update_file(self, file_type: AssetType, file_path: str, version: int) -> bool:
        key = file_type.value
        self.manifest_json[key]['version'] = version
        # Use POSIX paths (forward slashes) for cross-platform compatibility
        self.manifest_json[key]['path'] = Path(file_path).as_posix()
        self.logger.info(f"Manifest updated successfully for asset type: {key}, version: {version}, file_path: {file_path}")
        return self.io_controller.write_json(self.manifest_path, self.manifest_json)

    @try_catch
    def update_metadata(self, key: str, value: Any) -> bool:
        if 'metadata' not in self.manifest_json:
            self.manifest_json['metadata'] = {}

        self.manifest_json['metadata'][key] = value
        self.logger.info(f"Metadata updated successfully: {key} = {value}")
        return self.io_controller.write_json(self.manifest_path, self.manifest_json)

    def get_output_dir(self, asset_type: AssetType) -> str:
        return os.path.join(self.TOPIC, asset_type.value)
