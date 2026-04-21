import json
import os
from functools import wraps
from pathlib import Path
from typing import Dict, Any, Optional, List
from filelock import FileLock

from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.enums import AssetType
from scripts.logging_config import get_utility_logger
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.utility.config import MANIFEST_FILE


def with_file_lock(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        lock_path = self.manifest_path.replace('.json', '.lock')
        lock = FileLock(lock_path)
        with lock:
            self.manifest_json = self.io_controller.read_json(self.manifest_path)
            result = func(self, *args, **kwargs)
            return result
    return wrapper


class ManifestController:

    def __init__(self):
        self.logger = get_utility_logger('ManifestController')
        self.io_controller = SystemIOController()
        self.TOPIC = None
        self.manifest_path = "Outputs/{topic}/manifest.json"
        self.manifest_json = {}

    def set_topic(self, topic: str) -> None:
        self.TOPIC = topic
        self.manifest_path = MANIFEST_FILE.format(topic=topic)
        video_id = topic.rsplit("-v2", 1)[0] if topic else "--"
        self.logger = get_utility_logger('ManifestController', video_id=video_id)
        self._ensure_manifest_exists()
        self.manifest_json = self.io_controller.read_json(self.manifest_path)
        

    @with_file_lock
    def set_dimensions(self) -> None:
        video_ratio = self.manifest_json['metadata']['video_ratio']

        # Parse ratio format like "16/9", "9/16", "16:9", "9:16"
        # Default to portrait (9/16) if parsing fails
        try:
            # Replace : with / for consistent parsing
            ratio_str = video_ratio.replace(':', '/')
            parts = ratio_str.split('/')
            if len(parts) == 2:
                width_ratio = int(parts[0])
                height_ratio = int(parts[1])

                # Calculate dimensions based on ratio
                # Use 1080 as the base for the smaller dimension
                if width_ratio > height_ratio:
                    # Landscape (e.g., 16/9)
                    viewport_height = 1080
                    viewport_width = int(viewport_height * width_ratio / height_ratio)
                else:
                    # Portrait (e.g., 9/16)
                    viewport_width = 1080
                    viewport_height = int(viewport_width * height_ratio / width_ratio)
            else:
                # Fallback for old format
                viewport_width = 1080
                viewport_height = 1920
        except (ValueError, AttributeError):
            # Default to portrait dimensions
            viewport_width = 1080
            viewport_height = 1920

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
                    "video_ratio": "9:16",
                    "video_style": "vox"
                },
                "Research": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0,
                    "subagents_completed": []
                },
                "Scripts": {
                    "version": 1,
                    "path": f"Outputs/{self.TOPIC}/Scripts/script-user-input.md",
                    "current_gen_version": 1,
                    "subagents_completed": []
                },
                "Audio": {
                    "version": 0,
                    "path": None,
                    "transcript_path": None,
                    "current_gen_version": 0,
                    "subagents_completed": []
                },
                "Direction": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0,
                    "subagents_completed": []
                },
                "Assets": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0,
                    "subagents_completed": []
                },
                "Design": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0,
                    "subagents_completed": []
                },
                "Video": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0,
                    "subagents_completed": []
                },
                "Transcript": {
                    "version": 0,
                    "path": None,
                    "current_gen_version": 0,
                    "subagents_completed": []
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

    def _get_video_url_data(self) -> Dict[str, List[str]]:
        video_url_path = ClaudeCliConfig.VIDEO_URL_PATH
        return self.io_controller.read_json(video_url_path, check_exists=False) or {}

    def get_deployed_videos(self) -> Optional[List[str]]:
        video_url_path = ClaudeCliConfig.VIDEO_URL_PATH
        lock_path = video_url_path.replace('.json', '.lock')
        lock = FileLock(lock_path)
        with lock:
            video_data = self._get_video_url_data()
        all_urls = []
        for urls in video_data.values():
            all_urls.extend(urls)
        return all_urls

    def update_deployed_videos(self, video_url: str) -> bool:
        video_url_path = ClaudeCliConfig.VIDEO_URL_PATH
        lock_path = video_url_path.replace('.json', '.lock')
        lock = FileLock(lock_path)
        with lock:
            video_data = self._get_video_url_data()
            if self.TOPIC not in video_data:
                video_data[self.TOPIC] = []
            video_data[self.TOPIC].append(video_url)
            self.io_controller.write_json(video_url_path, video_data)
        return True

    @with_file_lock
    def get_current_gen_version(self, asset_type: AssetType) -> Optional[int]:
        return self.manifest_json[asset_type.value].get('current_gen_version', 0)

    @with_file_lock
    def increment_gen_version(self, asset_type: AssetType) -> int:
        version = self.manifest_json[asset_type.value].get('version') or 0
        current_gen = self.manifest_json[asset_type.value].get('current_gen_version', 0)

        if current_gen == version:
            self.manifest_json[asset_type.value]['current_gen_version'] = version + 1
            self.manifest_json[asset_type.value]['subagents_completed'] = []
            self.manifest_json[asset_type.value]['subagents_claimed'] = []
            self.io_controller.write_json(self.manifest_path, self.manifest_json)

        return self.manifest_json[asset_type.value]['current_gen_version']

    @with_file_lock
    @try_catch
    def update_file(self, file_type: AssetType, file_path: str, version: int) -> bool:
        key = file_type.value
        self.manifest_json[key]['version'] = version
        self.manifest_json[key]['path'] = Path(file_path).as_posix()
        self.logger.info(f"Manifest updated successfully for asset type: {key}, version: {version}, file_path: {file_path}")
        return self.io_controller.write_json(self.manifest_path, self.manifest_json)

    @with_file_lock
    @try_catch
    def update_metadata(self, key: str, value: Any) -> bool:
        if 'metadata' not in self.manifest_json:
            self.manifest_json['metadata'] = {}

        self.manifest_json['metadata'][key] = value
        self.logger.info(f"Metadata updated successfully: {key} = {value}")
        return self.io_controller.write_json(self.manifest_path, self.manifest_json)

    def get_output_dir(self, asset_type: AssetType) -> str:
        return os.path.join(self.TOPIC, asset_type.value)



