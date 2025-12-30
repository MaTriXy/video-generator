"""
Asset Generator Post-Process - Extracts SVGs from single file and versions them.
"""

import re
import sys
import os
from typing import Optional, Tuple, List, Dict
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig, AssetType
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController
from scripts.logging_config import set_console_logging


class AssetGeneratorPostProcess(BasePostProcess):

    def __init__(self, topic: str):
        super().__init__(
            logger_name='AssetGeneratorPostProcess',
            log_file_name='asset-generator-post-process',
            topic=topic,
            asset_type=AssetType.ASSETS,
        )
        self.metadata_controller = VideoStepMetadataController()

    @try_catch
    def _extract_composition(self, svg_content: str, asset_name: str = "") -> str:
        """
        Extract composition description from SVG comment.
        Looks for pattern: <!-- COMPOSITION: <description> -->
        Returns the composition string or empty string if not found.
        """
        match = re.search(r'<!--\s*COMPOSITION:\s*(.+?)\s*-->', svg_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        self.logger.warning(f"No composition comment found in {asset_name}, defaulting to empty")
        return ""

    @try_catch
    def extract_svgs_from_file(self, file_path: Path) -> List[Dict[str, str]]:
        content = file_path.read_text(encoding='utf-8')
        pattern = r'<!--\s*ASSET:\s*(\S+)\s*-->\s*((?:<!--\s*COMPOSITION:[^>]+-->\s*)?<svg[\s\S]*?</svg>)'
        matches = re.findall(pattern, content, re.IGNORECASE)

        assets = []
        for asset_name, svg_content in matches:
            assets.append({'name': asset_name.strip(), 'content': svg_content.strip()})

        self.logger.info(f"Extracted {len(assets)} assets from file")
        return assets

    @try_catch
    def save_assets_to_dir(self, target_dir: Path, assets: List[Dict[str, str]]) -> List[Dict]:
        saved_assets = []
        for asset in assets:
            asset_name = asset['name']
            svg_content = asset['content']
            dest_file = target_dir / f"{asset_name}.svg"

            try:
                dest_file.write_text(svg_content, encoding='utf-8')
                composition = self._extract_composition(svg_content, asset_name)
                saved_assets.append({
                    "name": asset_name,
                    "path": str(dest_file).replace("\\", "/"),
                    "composition": composition
                })
            except Exception as e:
                self.logger.error(f"Failed to save {asset_name}: {str(e)}")

        return saved_assets

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[str]]:
        self.logger.info("Processing asset generator output")

        latest_path = Path(self.claude_cli_config.get_latest_path(self.asset_type))
        if not latest_path.exists():
            self.logger.error(f"Combined assets file not found: {latest_path}")
            return None, None

        assets = self.extract_svgs_from_file(latest_path)
        if not assets:
            self.logger.error("No assets extracted from file")
            return None, None

        self.gen_metadata_controller.set_metadata({"total_assets": len(assets)})

        latest_dir = latest_path.parent
        saved_assets = self.save_assets_to_dir(latest_dir, assets)
        if not saved_assets:
            self.logger.error("Failed to save any assets")
            return None, None

        latest_json = latest_dir / "latest_assets.json"
        self.file_io.write_json(str(latest_json), {"assets": saved_assets})

        file_path, version = self.output_controller.save_output(self.asset_type, str(latest_json))
        if not file_path:
            return None, None

        version_dir = Path(file_path).parent
        versioned_assets = self.save_assets_to_dir(version_dir, assets)

        self.file_io.write_json(file_path, {"assets": versioned_assets})
        self.manifest_controller.update_file(self.asset_type, file_path, version)

        return str(version), file_path

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
