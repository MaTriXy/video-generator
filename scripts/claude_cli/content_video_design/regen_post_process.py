import sys
import os
from typing import List, Optional, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.content_video_design.post_process import VideoDesignPostProcessing
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import set_console_logging


class VideoDesignRegenPostProcessing(VideoDesignPostProcessing):

    def __init__(self, topic: str, scenes: List[int]):
        super().__init__(topic=topic)
        self.scenes = scenes
        self.logger.info(f"Initialized regeneration post-processing for scenes: {scenes}")

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[int]]:
        self.logger.info(f"Processing regenerated video design output for scenes: {self.scenes}")

        total_scenes = self._get_total_scenes()
        if not total_scenes:
            self.logger.error("Could not determine total scenes from metadata")
            return None, None

        source_template = self.claude_cli_config.get_latest_path(self.asset_type)
        file_path, version = self.output_controller.save_scene_outputs(
            self.asset_type,
            source_template,
            total_scenes
        )

        if file_path and version:
            self.manifest_controller.update_file(self.asset_type, file_path, version)
            self.logger.info(f"Regenerated video design output processed for scenes: {self.scenes}")

        return file_path, version


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Regenerate post-process for specific scenes")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--scenes', type=str, required=True, help='Comma-separated scene indices (e.g., "0,2,3")')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging (default: True)')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    set_console_logging(args.log)

    scene_indices = [int(s.strip()) for s in args.scenes.split(',')]

    post_processor = VideoDesignRegenPostProcessing(topic=args.topic, scenes=scene_indices)

    success, file_path = post_processor.run()

    if success and file_path:
        post_processor.logger.info("✓ Successfully processed regenerated video design")
        post_processor.logger.info(f"✓ Output file: {file_path}")
    else:
        post_processor.logger.error("✗ Failed to process regenerated video design")
        sys.exit(1)

    post_processor.logger.info("✓ Video design regeneration post-processing completed successfully")
