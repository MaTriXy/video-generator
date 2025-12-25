from typing import Any, Optional

from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.utils.singleton import SingletonMeta
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.enums import AssetType

default_metadata = {
    "manifest": {},
    "generated":{"asset_type": None,"version": 0}
}

delete_from_manifest = {
    AssetType.SCRIPT.value: [AssetType.AUDIO.value,AssetType.VIDEO.value,AssetType.DIRECTION.value,AssetType.DESIGN.value],
    AssetType.AUDIO.value: [AssetType.VIDEO.value,AssetType.DIRECTION.value,AssetType.DESIGN.value],
    AssetType.DIRECTION.value: [AssetType.VIDEO.value,AssetType.DESIGN.value,AssetType.ASSETS.value],
    AssetType.ASSETS.value: [AssetType.VIDEO.value,AssetType.DESIGN.value],
    AssetType.DESIGN.value: [AssetType.VIDEO.value],
    AssetType.VIDEO.value: [],
}

class GenMetadataController(metaclass=SingletonMeta):

    def __init__(self, asset_type: AssetType):
        self.manifest_controller = ManifestController();
        self.asset_type = asset_type
        self.io_controller = SystemIOController()
        self._metadata = self.read_metadata()

    def save_metadata(self) -> None:
        version = self.manifest_controller.get_current_gen_version(self.asset_type)
        metadata_path = ClaudeCliConfig.get_gen_metadata_path(self.asset_type, version)
        manifest_data={**self.manifest_controller.manifest_json}
        for asset_type in AssetType:
            if asset_type.value in manifest_data:
                manifest_data[asset_type.value] = manifest_data[asset_type.value].get('path',"")

        for asset_type in delete_from_manifest[self.asset_type.value]:
            if asset_type in manifest_data:
                del manifest_data[asset_type]
        self._metadata['manifest'] = manifest_data
        self._metadata['generated']['asset_type'] = self.asset_type.value
        self._metadata['generated']['version'] = version
        self.io_controller.write_json(metadata_path, self._metadata)

    def read_metadata(self) -> Any:
            version = self.manifest_controller.get_current_gen_version(self.asset_type)
            metadata_path = ClaudeCliConfig.get_gen_metadata_path(self.asset_type, version)
            return self.io_controller.read_json(metadata_path,False) or default_metadata

    def set_metadata(self, metadata: Any) -> None:
        if self.asset_type.value not in self._metadata:
            self._metadata[self.asset_type.value] = {}
        self._metadata[self.asset_type.value] = {**self._metadata[self.asset_type.value], **metadata}