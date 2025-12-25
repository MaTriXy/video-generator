import sys
import os
from typing import List, Optional, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.content_video.post_process import VideoContentPostProcessing
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import set_console_logging


class VideoSceneRegenPostProcessing(VideoContentPostProcessing):

    def __init__(self, topic: str, scenes: List[int]):
        super().__init__(topic=topic)
        self.scenes = scenes
        self.logger.info(f"Initialized regeneration post-processing for scenes: {scenes}")

    @try_catch
    def combine_and_save_scenes(self) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"Combining all scenes including regenerated scenes: {self.scenes}")
        combined_content = self.combine_scene_files()
        if not combined_content:
            self.logger.error("Failed to combine scene files")
            return False, None

        version_dir, version = self.create_version_directory()
        if not version_dir:
            return False, None

        if not self.copy_scene_files_to_version_dir(version_dir):
            return False, None

        final_output_path = version_dir / "Video.tsx"
        self.file_io.write_text(str(final_output_path), combined_content)
        self.logger.info(f"Saved combined video player to: {final_output_path}")

        file_path_for_manifest = str(final_output_path.relative_to(self.claude_cli_config.BASE_OUTPUT_PATH))
        self.manifest_controller.update_file(self.asset_type, file_path_for_manifest, version)

        self.logger.info(f"Regenerated video components processed for scenes: {self.scenes}")
        return True, file_path_for_manifest


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

    post_processor = VideoSceneRegenPostProcessing(topic=args.topic, scenes=scene_indices)

    success, file_path = post_processor.run()

    if success and file_path:
        post_processor.logger.info("✓ Successfully processed regenerated video components")
        post_processor.logger.info(f"✓ Output file: {file_path}")
    else:
        post_processor.logger.error("✗ Failed to process regenerated video components")
        sys.exit(1)

    post_processor.logger.info("✓ Video component regeneration post-processing completed successfully")
