"""
React Video Direction Pre-Process - Handles prompt variable preparation for video direction generation.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.base_pre_process import BasePreProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.utility.join_lines import truncate_content


class VideoDirectionPreProcess(BasePreProcess):

    def __init__(self, topic: str):
        super().__init__(
            asset_type=AssetType.DIRECTION,
            logger_name='VideoDirectionPreProcess',
            log_file_name="content-video-direction-pre-process",
            topic=topic,
        )

    @try_catch
    def save_config_prompts(self) -> None:
        sub_prompts = self.fetch_sub_prompts(["examples"])
        if not sub_prompts:
            return

        examples_content = sub_prompts.get("examples", "")
        truncated_content = truncate_content(examples_content)

        example_path = Path(ClaudeCliConfig.BASE_OUTPUT_PATH) / self.claude_cli_config.topic / "Direction" / "examples" / "example.md"
        self.file_io.write_text(str(example_path), truncated_content)
        self.logger.info(f"Wrote example to: {example_path}")

    def save_prompt(self):
        artstyle_json = self.load_artstyle("direction")
        variables = self.build_prompt_variables()
        variables["art_style"] = artstyle_json

        metadata = self.get_metadata()

        director_instructions = metadata.get("director_instructions", "")
        if director_instructions:
            variables["visual_instructions"] = f"<User_visual_instructions>\n{director_instructions}\n</User_visual_instructions>"
        else:
            variables["visual_instructions"] = ""

        prompt = self.build_prompt(variables=variables)
        self.save_config_prompts()

        prompt_header = f"<video_id>{self.video_id}</video_id>\n\n"
        prompt = f"{prompt_header}{prompt}"

        uploaded_assets_raw = metadata.get("uploaded_assets", [])
        if uploaded_assets_raw:
            asset_instructions = "\n\n<uploaded_assets_instructions>\n"
            asset_instructions += "The user has uploaded the following assets for use in this video. You MUST use these uploaded assets in your direction.\n"
            asset_instructions += "For each uploaded asset:\n"
            asset_instructions += "- Include it in the `required_assets` array with `\"asset-type\": \"uploaded\"` and its original `url` field preserved.\n"
            asset_instructions += "- Use a clean short name (e.g. 'hotairballoon') as the `name` in required_assets, and reference it with @name in scene descriptions.\n"
            asset_instructions += "- Do NOT create a new asset that duplicates what an uploaded asset already provides.\n"
            asset_instructions += "</uploaded_assets_instructions>"
            prompt = f"{prompt}{asset_instructions}"

        self.save_prompt_to_file(prompt)
        self.force_logging(f" Saved video direction prompt to: {self.prompt_path}")


    def read_script_markdown(self) -> str:
        """Read script markdown file from path specified in manifest."""
        content_data = self.manifest_controller.get_field(AssetType.SCRIPT)
        file_path = content_data.get('path') if content_data else None

        if not file_path:
            raise ValueError("No script path found in manifest. Script step may not have completed.")

        script_text = self.file_io.read_text(file_path)
        if not script_text:
            raise ValueError(f"Script file is empty or unreadable: {file_path}")

        self.logger.info(f"Read script from: {file_path} ({len(script_text)} characters)")
        return script_text.strip()

    def build_prompt_variables(self) -> Dict[str, Any]:
        """
        Build variables for video direction generation prompt.
        Simplified for video-centric approach.
        """
        self.gen_metadata_controller.set_metadata({"type":"claude_cli"})
        self.gen_metadata_controller.save_metadata()
        # Get script markdown
        script_markdown = self.read_script_markdown()

        course_metadata = self.get_metadata()

        uploaded_assets_raw = course_metadata.get("uploaded_assets", [])
        uploaded_assets_json = json.dumps(uploaded_assets_raw, indent=2) if uploaded_assets_raw else "[]"

        variables = {
            **course_metadata,
            "script": script_markdown,
            "script_markdown": " ",
            "uploaded_assets": uploaded_assets_json,
        }

        self.logger.info(f"Built prompt variables: {list(variables.keys())}")

        return variables


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-process video direction prompt")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    args = parser.parse_args()

    pre_process = VideoDirectionPreProcess(topic=args.topic)
    pre_process.run()
