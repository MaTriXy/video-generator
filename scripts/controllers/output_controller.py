import os
import re
from time import sleep
from typing import Any, Optional, Tuple
from pathlib import Path
from enum import Enum

from scripts.controllers.manifest_controller import ManifestController
from scripts.logging_config import get_utility_logger
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.enums import AssetType


class OutputController:

    def __init__(self):
        topic=ClaudeCliConfig.TOPIC
        BASE_OUTPUT_PATH=ClaudeCliConfig.BASE_OUTPUT_PATH
        self.base_path = f"{BASE_OUTPUT_PATH}/{topic}".format(BASE_OUTPUT_PATH=BASE_OUTPUT_PATH,topic=topic)
        self.logger = get_utility_logger('OutputController')
        self.io_controller = SystemIOController()
        self._create_output_directories()
        self.manifest_controller = ManifestController()

    def _create_output_directories(self) -> None:
        """Create the base output folder and all asset type subdirectories."""
        if not self.io_controller.exists(self.base_path):
            self.io_controller.ensure_directory(self.base_path)
            self.logger.info(f"Created base output directory: {self.base_path}")

        for asset_type in AssetType:
            asset_dir = os.path.join(self.base_path, asset_type.value)
            if not self.io_controller.exists(asset_dir):
                self.io_controller.ensure_directory(asset_dir)
                self.logger.info(f"Created asset directory: {asset_dir}")
        
    def _list_files(self, relative_dir: str = '') -> list:
        full_dir = os.path.join(self.base_path, relative_dir) if relative_dir else self.base_path
        if not self.io_controller.exists(full_dir):
            return []
        return self.io_controller.list_files(full_dir)

    def _write_file(self, file_path: str, content: Any, extension: str) -> bool:
        try:
            if extension == 'json':
                return self.io_controller.write_json(file_path, content)
            else:
                return self.io_controller.write_text(file_path, str(content))
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {str(e)}")
            return False

    def read_llm_file(self, asset_type: AssetType) -> Any:
        file_path = ClaudeCliConfig.get_latest_path(asset_type)
        if not file_path:
            raise ValueError(f"No file path provided for asset type: {asset_type}")
        return self.io_controller.read_json(file_path)

    def read_output(self, asset_type: AssetType,scene_index: Optional[int] = 0) -> Any:
        content_data = self.manifest_controller.get_field(asset_type)
        file_path = content_data.get('path')
        if not file_path:
            self.logger.error(f"No file path provided for asset type: {asset_type}")
            return None
        if file_path.endswith('.json'):
            return self.io_controller.read_json(file_path.format(scene_index=scene_index))
        elif file_path.endswith('.md'):
            return self.io_controller.read_text(file_path.format(scene_index=scene_index))


    def save_output(self, asset_type: AssetType, source_file: str) -> Tuple[Optional[str], Optional[int]]:
        if not self.io_controller.exists(source_file):
            self.logger.error(f"Source file does not exist: {source_file}")
            return None, None

        version = self.manifest_controller.get_current_gen_version(asset_type)
        self.logger.info(f"Latest version: {version}")
        extension = Path(source_file).suffix.lstrip('.')
        filename = f"{asset_type.value}-v{version}.{extension}"

        version_dir = os.path.join(self.base_path, asset_type.value, f"v{version}")

        if not self.io_controller.exists(version_dir):
            self.io_controller.ensure_directory(version_dir)

        dest_path = os.path.join(version_dir, filename)

        try:
            self.io_controller.copy_file(source_file, dest_path)
            self.logger.info(f"Copied {source_file} to {dest_path}")
            return dest_path, version
        except Exception as e:
            self.logger.error(f"Failed to copy file: {str(e)}")
            return None, None

    def save_scene_outputs(self, asset_type: AssetType, source_file_template: str, total_scenes: int) -> Tuple[Optional[str], Optional[int]]:
        """
        Save multiple scene files to a versioned folder.

        Args:
            asset_type: The asset type (e.g., DESIGN, VIDEO)
            source_file_template: Path template with {scene_index} placeholder (e.g., "Outputs/Design/latest_{scene_index}.json")
            total_scenes: Total number of scenes to process

        Returns:
            Tuple of (path_template_with_version, version) where path_template contains {scene_index} placeholder
        """
        version = self.manifest_controller.get_current_gen_version(asset_type)
        version_dir = os.path.join(self.base_path, asset_type.value, f"v{version}")
        if not self.io_controller.exists(version_dir):
            self.io_controller.ensure_directory(version_dir)

        extension = Path(source_file_template).suffix.lstrip('.')
        dest_filename_template = f"{asset_type.value}_{{scene_index}}.{extension}"
        dest_path_template = os.path.join(version_dir, dest_filename_template)

        copied_count = 0
        for scene_index in range(total_scenes):
            source_file = source_file_template.replace("{scene_index}", str(scene_index))

            if not self.io_controller.exists(source_file):
                self.logger.warning(f"Scene file does not exist: {source_file}")
                continue

            dest_path = dest_path_template.replace("{scene_index}", str(scene_index))

            try:
                self.io_controller.copy_file(source_file, dest_path)
                self.logger.info(f"Copied scene {scene_index}: {source_file} to {dest_path}")
                copied_count += 1
            except Exception as e:
                self.logger.error(f"Failed to copy scene {scene_index}: {str(e)}")

        if copied_count == 0:
            self.logger.error("No scene files were copied")
            return None, None

        self.logger.info(f"Successfully copied {copied_count}/{total_scenes} scene files to {version_dir}")
        return dest_path_template, version

    def save_asset_outputs(self, asset_type: AssetType, source_file: str) -> Tuple[Optional[str], Optional[int]]:
        if not self.io_controller.exists(source_file):
            self.logger.error(f"Source file does not exist: {source_file}")
            return None, None

        output_data = self.io_controller.read_json(source_file)
        if not output_data or "assets" not in output_data:
            self.logger.error("Invalid output: missing 'assets' array")
            return None, None

        version = self.manifest_controller.get_current_gen_version(asset_type)
        latest_dir = str(Path(source_file).parent)
        version_dir = os.path.join(self.base_path, asset_type.value, f"v{version}")

        if not self.io_controller.exists(version_dir):
            self.io_controller.ensure_directory(version_dir)

        svg_files = list(Path(latest_dir).glob("*.svg"))
        copied_count = 0

        for svg_file in svg_files:
            dest_file = Path(version_dir) / svg_file.name
            try:
                self.io_controller.copy_file(str(svg_file), str(dest_file))
                self.logger.info(f"Copied asset: {svg_file.name}")
                copied_count += 1
            except Exception as e:
                self.logger.error(f"Failed to copy {svg_file.name}: {str(e)}")

        for asset in output_data["assets"]:
            if "path" in asset:
                filename = Path(asset["path"]).name
                new_path = str(Path(version_dir) / filename)
                asset["path"] = new_path.replace("\\", "/")

        extension = Path(source_file).suffix.lstrip('.')
        output_filename = f"{asset_type.value}-v{version}.{extension}"
        dest_path = os.path.join(version_dir, output_filename)

        try:
            self.io_controller.write_json(dest_path, output_data)
            self.logger.info(f"Successfully copied {copied_count} asset files to {version_dir}")
            return dest_path, version
        except Exception as e:
            self.logger.error(f"Failed to save output: {str(e)}")
            return None, None