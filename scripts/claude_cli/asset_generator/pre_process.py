"""
Asset Generator Pre-Process - Extracts required_assets from Direction and generates prompt.
"""

import sys
import os
from typing import Dict, Any, List

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.base_pre_process import BasePreProcess
from scripts.controllers.utils.decorators.try_catch import try_catch


class AssetGeneratorPreProcess(BasePreProcess):

    def __init__(self, topic: str):
        super().__init__(
            asset_type=AssetType.ASSETS,
            logger_name='AssetGeneratorPreProcess',
            log_file_name="asset-generator-pre-process",
            topic=topic,
            gen_prompt=True,
        )

        self.asset_meta_data_path = self.claude_cli_config.get_metadata_path(self.asset_type)

    @try_catch
    def extract_required_assets(self) -> List[Dict[str, str]]:
        """Extract required_assets from Direction output and return them."""
        direction_manifest = self.manifest_controller.get_field(AssetType.DIRECTION)
        direction_path = direction_manifest.get('path') if direction_manifest else None

        if not direction_path:
            self.logger.error("No Direction path found in manifest")
            raise ValueError("No Direction path found in manifest")

        self.logger.info(f"Reading Direction from: {direction_path}")

        direction = self.file_io.read_json(direction_path)
        if not direction:
            self.logger.error(f"Failed to read Direction file: {direction_path}")
            raise ValueError(f"Failed to read Direction file: {direction_path}")

        required_assets = direction.get('required_assets')

        if required_assets is None:
            self.logger.error("'required_assets' array does not exist in Direction file")
            raise ValueError("'required_assets' array does not exist in Direction file")

        if not required_assets:
            self.logger.warning("required_assets array exists but is empty - no assets to generate")
            return []

        self.logger.info(f"Found {len(required_assets)} assets to generate")
        return required_assets

    @try_catch
    def build_prompt_variables(self) -> Dict[str, Any]:
        """Build variables for the asset generation prompt."""
        required_assets = self.extract_required_assets()
        course_metadata = self.get_metadata()

        variables = {
            **course_metadata,
            "required_assets": required_assets,
        }

        self.logger.info(f"Built prompt variables: {list(variables.keys())}")
        return variables

    @try_catch
    def save_prompt(self) -> None:
        """Generate and save the asset generation prompt from langfuse."""
        variables = self.build_prompt_variables()
        prompt = self.build_prompt(variables=variables)
        self.save_prompt_to_file(prompt)
        self.logger.info(f"Saved asset generation prompt to: {self.prompt_path}")

        required_assets = variables.get('required_assets', [])
        asset_names = [asset.get('name', '') for asset in required_assets]

        output = {
            "total_assets": len(required_assets),
            "asset_names": asset_names
        }
        self.file_io.write_json(self.asset_meta_data_path, output)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-process asset generator")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for asset generation')
    args = parser.parse_args()

    pre_process = AssetGeneratorPreProcess(topic=args.topic)
    pre_process.run()
