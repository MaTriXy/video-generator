"""
Asset Generator Pre-Process - Extracts required_assets from Direction and generates prompt.
"""

import sys
import os
import uuid
from pathlib import Path
from typing import Dict, Any, List

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.base_pre_process import BasePreProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController


class AssetGeneratorPreProcess(BasePreProcess):

    def __init__(self, topic: str):
        super().__init__(
            asset_type=AssetType.ASSETS,
            logger_name='AssetGeneratorPreProcess',
            log_file_name="asset-generator-pre-process",
            topic=topic,
            gen_prompt=True,
        )

        self.metadata_controller = VideoStepMetadataController(topic)
        self._skip_agent = False

        artstyle_config_path = self.claude_cli_config.get_artstyle_config_path(AssetType.ASSETS)
        self.artstyle_config = self.file_io.read_json(artstyle_config_path)

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

        # Separate uploaded assets from assets that need generation
        uploaded = [a for a in required_assets if a.get("asset-type") == "uploaded"]
        to_generate = [a for a in required_assets if a.get("asset-type") != "uploaded"]

        if uploaded:
            self.logger.info(f"Found {len(uploaded)} uploaded assets (will skip generation): {[a.get('name') for a in uploaded]}")
            # Store uploaded assets so post-process can include them directly
            self._uploaded_assets_from_direction = uploaded

        # Assign unique asset_id to each asset for analytics tracking
        for asset in to_generate:
            if "asset_id" not in asset:
                asset["asset_id"] = asset.get("name", uuid.uuid4().hex[:8])

        self.logger.info(f"Found {len(to_generate)} assets to generate")
        return to_generate

    @try_catch
    def build_prompt_variables(self) -> Dict[str, Any]:
        """Build variables for the asset generation prompt."""
        required_assets = self.extract_required_assets()
        course_metadata = self.get_metadata()

        video_style = course_metadata.get("video_style", "")
        style_config = self.artstyle_config.get(video_style) if video_style else None
        asset_artstyle = { "color_theme": style_config.get("palette", []) if style_config else "" }

        variables = {
            **course_metadata,
            "required_assets": required_assets,
            "asset_artstyle": asset_artstyle,
        }

        self.logger.info(f"Built prompt variables: {list(variables.keys())}")
        return variables

    @try_catch
    def save_prompt(self) -> None:
        """Generate and save the asset generation prompt to disk."""
        variables = self.build_prompt_variables()
        required_assets = variables.get('required_assets', [])

        if not required_assets:
            self.logger.info("No required assets — skipping prompt generation")
            self._skip_agent = True
            output = {"total_assets": 0, "asset_names": []}
            self.metadata_controller.write(self.asset_type, output)
            return

        prompt = self.build_prompt(variables=variables)

        metadata = self.manifest_controller.get_metadata()
        video_style = metadata.get("video_style")

        output_directory = str(Path(project_root) / Path(self.claude_cli_config.get_latest_path(self.asset_type)).parent)
        prompt_header = f"video_style: {video_style}\noutput_directory: {output_directory}\n\n"
        prompt = f"{prompt_header}{prompt}"

        self.save_prompt_to_file(prompt)
        self.logger.info(f"Saved asset generation prompt to: {self.prompt_path}")

        asset_names = [asset.get('name', '') for asset in required_assets]

        output = {
            "total_assets": len(required_assets),
            "asset_names": asset_names
        }
        self.metadata_controller.write(self.asset_type, output)


    def run(self):
        result = super().run()
        if self._skip_agent:
            self.logger.info("Signalling agent skip — no assets to generate")
            return None
        return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-process asset generator")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for asset generation')
    args = parser.parse_args()

    pre_process = AssetGeneratorPreProcess(topic=args.topic)
    pre_process.run()
