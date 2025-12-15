"""
React Video Direction Pre-Process - Handles prompt variable preparation for video direction generation.
"""

import sys
import os
from typing import Dict, Any


# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.base_pre_process import BasePreProcess
from scripts.controllers.utils.decorators.try_catch import try_catch


class VideoDirectionPreProcess(BasePreProcess):

    def __init__(self, topic: str):
        super().__init__(
            asset_type=AssetType.DIRECTION,
            logger_name='VideoDirectionPreProcess',
            log_file_name="content-video-direction-pre-process",
            topic=topic,
        )

    @try_catch
    def save_prompt(self):
        prompt = self.build_prompt(variables=self.build_prompt_variables())
        self.save_prompt_to_file(prompt)
        self.force_logging(f" Saved video direction prompt to: {self.prompt_path}")


    @try_catch
    def read_script_markdown(self) -> str:
        """Read script markdown file from path specified in manifest."""
        content_data = self.manifest_controller.get_field(AssetType.SCRIPT)
        file_path = content_data.get('path') if content_data else None

        if not file_path:
            self.logger.error("No script path found in manifest")
            return ""

        script_text = self.file_io.read_text(file_path)
        if not script_text:
            self.logger.error(f"Failed to read script from: {file_path}")
            return ""

        self.logger.info(f"Read script from: {file_path} ({len(script_text)} characters)")
        return script_text.strip()

    @try_catch
    def build_prompt_variables(self) -> Dict[str, Any]:
        """
        Build variables for video direction generation prompt.
        Simplified for video-centric approach.
        """
        self.gen_metadata_controller.set_metadata({"type":"claude_cli"})
        self.gen_metadata_controller.save_metadata()
        # Get script markdown
        script_markdown = self.read_script_markdown()
        if not script_markdown:
            raise ValueError("No script markdown found")

        course_metadata = self.get_metadata()

        variables = {
            **course_metadata,
            "script": script_markdown,
            "script_markdown": " ",
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
