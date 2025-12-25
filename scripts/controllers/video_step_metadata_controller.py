import os
from typing import Any, Dict, Optional

from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.controllers.utils.singleton import SingletonMeta
from scripts.enums import AssetType
from scripts.logging_config import get_utility_logger


class VideoStepMetadataController(metaclass=SingletonMeta):

    def __init__(self):
        self.io_controller = SystemIOController()
        self.logger = get_utility_logger('VideoStepMetadataController')

    def get_metadata_path(self, asset_type: AssetType) -> str:
        return ClaudeCliConfig.get_metadata_path(asset_type)

    def read(self, asset_type: AssetType) -> Dict[str, Any]:
        metadata_path = self.get_metadata_path(asset_type)
        if not os.path.exists(metadata_path):
            return {}
        return self.io_controller.read_json(metadata_path) or {}

    def write(self, asset_type: AssetType, metadata: Dict[str, Any]) -> bool:
        metadata_path = self.get_metadata_path(asset_type)
        return self.io_controller.write_json(metadata_path, metadata)

    def update(self, asset_type: AssetType, updates: Dict[str, Any]) -> bool:
        metadata = self.read(asset_type)
        metadata.update(updates)
        return self.write(asset_type, metadata)

    def get_field(self, asset_type: AssetType, field: str, default: Any = None) -> Any:
        metadata = self.read(asset_type)
        return metadata.get(field, default)

    def get_total_scenes(self, asset_type: AssetType) -> int:
        return self.get_field(asset_type, 'total_scenes', 0)

    def get_total_assets(self) -> int:
        return self.get_field(AssetType.ASSETS, 'total_assets', 0)
