"""
Video Design Post-Processing - Handles scene design output saving and manifest updates.
Saves all scene design files to a versioned folder and updates manifest with path template.
"""

import sys
import os
from typing import Optional, Tuple
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig, AssetType
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController
from scripts.logging_config import set_console_logging


class VideoDesignPostProcessing(BasePostProcess):
    """
    Post-processing for scene design generation.
    Handles saving multiple scene files to a versioned folder.
    """

    def __init__(self, topic: str):
        super().__init__(
            logger_name='VideoDesignPostProcessing',
            log_file_name='content-video-design-post-process',
            topic=topic,
            asset_type=AssetType.DESIGN,
        )
        self.metadata_controller = VideoStepMetadataController()

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[int]]:
        self.logger.info("Processing video design output")

        total_scenes = self.metadata_controller.get_total_scenes(self.asset_type)
        if not total_scenes:
            self.logger.error("Could not determine total scenes from metadata")
            return None, None
        self.gen_metadata_controller.set_metadata({"total_scenes": total_scenes})
        self.logger.info(f"Processing {total_scenes} scene design files")

        source_template = self.claude_cli_config.get_latest_path(self.asset_type)
        file_path, version = self.output_controller.save_scene_outputs(
            self.asset_type,
            source_template,
            total_scenes
        )

        if file_path and version:
            self.manifest_controller.update_file(self.asset_type, file_path, version)
            self.logger.info("Video design output processed successfully")

        return file_path, version

    @try_catch
    def process(self) -> Tuple[bool, Optional[str]]:
        file_path, version = self.process_output()

        if not version or not file_path:
            self.logger.error("Failed to process video design output")
            return False, None

        return True, file_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post-process video design")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging (default: True)')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    set_console_logging(args.log)

    post_processor = VideoDesignPostProcessing(topic=args.topic)

    success, file_path = post_processor.run()

    if success and file_path:
        post_processor.logger.info("✓ Successfully processed video design")
        post_processor.logger.info(f"✓ Output file: {file_path}")
    else:
        post_processor.logger.error("✗ Failed to process video design")
        sys.exit(1)

    post_processor.logger.info("✓ Video design post-processing completed successfully")
