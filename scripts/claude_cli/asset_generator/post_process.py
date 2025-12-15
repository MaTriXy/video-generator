"""
Asset Generator Post-Process - Versions SVG assets.
"""

import sys
import os
from typing import Optional, Tuple
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig, AssetType
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import set_console_logging


class AssetGeneratorPostProcess(BasePostProcess):

    def __init__(self, topic: str):
        super().__init__(
            logger_name='AssetGeneratorPostProcess',
            log_file_name='asset-generator-post-process',
            topic=topic,
            asset_type=AssetType.ASSETS,
        )
        self.asset_meta_data_path = self.claude_cli_config.get_metadata_path(self.asset_type)

    @try_catch
    def _get_asset_metadata(self) -> tuple:
        metadata = self.file_io.read_json(self.asset_meta_data_path)
        total_assets = metadata.get('total_assets', 0)
        asset_names = metadata.get('asset_names', [])
        return total_assets, asset_names

    @try_catch
    def copy_asset_files_to_version_dir(self, version_dir: Path, asset_names: list) -> Tuple[bool, list]:
        self.logger.info(f"Copying asset files to {version_dir}")

        latest_path_template = self.claude_cli_config.get_latest_path(self.asset_type)
        latest_dir = Path(latest_path_template).parent

        copied_assets = []
        for asset_name in asset_names:
            source_file = latest_dir / f"latest_{asset_name}.svg"
            dest_file = version_dir / f"{asset_name}.svg"

            if not source_file.exists():
                self.logger.warning(f"Asset file does not exist: {source_file}")
                continue

            try:
                dest_file.write_text(source_file.read_text(encoding='utf-8'), encoding='utf-8')
                self.logger.info(f"Copied {asset_name}.svg to version directory")

                copied_assets.append({
                    "name": asset_name,
                    "path": str(version_dir / f"{asset_name}.svg").replace("\\", "/")
                })
            except Exception as e:
                self.logger.error(f"Failed to copy asset {asset_name}: {str(e)}")

        self.logger.info(f"Successfully copied {len(copied_assets)}/{len(asset_names)} asset files")
        return len(copied_assets) > 0, copied_assets

    @try_catch
    def generate_asset_manifest(self, copied_assets: list, version_dir: Path, version: int) -> Optional[str]:
        asset_manifest = {
            "assets": copied_assets
        }

        manifest_path = version_dir / f"asset-manifest-v{version}.json"

        try:
            self.file_io.write_json(str(manifest_path), asset_manifest)
            self.logger.info(f"Generated asset manifest: {manifest_path}")
            return str(manifest_path)
        except Exception as e:
            self.logger.error(f"Failed to generate asset manifest: {str(e)}")
            return None

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[str]]:
        self.logger.info("Processing asset generator output")

        total_assets, asset_names = self._get_asset_metadata()
        if not total_assets or not asset_names:
            self.logger.error("Could not determine asset metadata")
            return None, None

        self.gen_metadata_controller.set_metadata({"total_assets": total_assets})
        self.logger.info(f"Processing {total_assets} asset files")

        version = self.manifest_controller.get_current_gen_version(self.asset_type)
        latest_path_template = self.claude_cli_config.get_latest_path(self.asset_type)
        latest_dir = Path(latest_path_template).parent
        version_dir = latest_dir.parent / f"v{version}"
        version_dir.mkdir(parents=True, exist_ok=True)

        success, copied_assets = self.copy_asset_files_to_version_dir(version_dir, asset_names)

        if not success:
            self.logger.error("Failed to copy asset files")
            return None, None

        manifest_path = self.generate_asset_manifest(copied_assets, version_dir, version)

        if not manifest_path:
            self.logger.error("Failed to generate asset manifest")
            return None, None

        self.manifest_controller.update_file(self.asset_type, manifest_path, version)
        self.logger.info("Asset generator output processed successfully")

        return str(version), manifest_path

    @try_catch
    def process(self) -> Tuple[bool, Optional[str]]:
        version, file_path = self.process_output()

        if not version or not file_path:
            self.logger.error("Failed to process asset generator output")
            return False, None

        return True, file_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post-process asset generator")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for asset generation')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging (default: True)')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    set_console_logging(args.log)

    post_processor = AssetGeneratorPostProcess(topic=args.topic)

    success, file_path = post_processor.run()

    if success and file_path:
        post_processor.logger.info("Successfully processed asset generator output")
        post_processor.logger.info(f"Output file: {file_path}")
    else:
        post_processor.logger.error("Failed to process asset generator output")
        sys.exit(1)

    post_processor.logger.info("Asset generator post-processing completed successfully")
