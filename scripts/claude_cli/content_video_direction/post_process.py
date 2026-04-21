import sys
import os
import asyncio
from pathlib import Path
from typing import Optional, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.enums import AssetType
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import set_console_logging


class VideoDirectionPostProcessing(BasePostProcess):

    def __init__(self, topic: str):
        super().__init__(
            logger_name='VideoDirectionPostProcessing',
            log_file_name='content-video-direction-post-process',
            topic=topic,
            asset_type=AssetType.DIRECTION,
        )

    def _extract_script_from_direction(self) -> Tuple[bool, Optional[str]]:
        source_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)

        if not self.file_io.exists(source_file):
            error_msg = f"Direction source file does not exist: {source_file}"
            self.logger.error(error_msg)
            return False, error_msg

        direction_data = self.file_io.read_json(source_file)

        if not direction_data or 'scenes' not in direction_data:
            error_msg = "Invalid direction data: missing 'scenes' array"
            self.logger.error(error_msg)
            return False, error_msg

        script_parts = []
        total_scenes = len(direction_data['scenes'])

        for scene_idx, scene in enumerate(direction_data['scenes']):
            narration = scene.get('audioTranscriptPortion', '')

            if not narration:
                self.logger.warning(f"Scene {scene_idx + 1}: No audioTranscriptPortion text found")
                continue

            script_parts.append(narration.strip())
            self.logger.info(f"Scene {scene_idx + 1}/{total_scenes}: Extracted {len(narration)} chars")

        if not script_parts:
            error_msg = "No audioTranscriptPortion found in any scene"
            self.logger.error(error_msg)
            return False, error_msg

        full_script = "\n\n".join(script_parts)

        script_output_path = self.claude_cli_config.get_final_path(AssetType.SCRIPT)
        Path(script_output_path).parent.mkdir(parents=True, exist_ok=True)

        success = self.file_io.write_text(script_output_path, full_script)

        if success:
            self.logger.info(f"✓ Extracted script from {total_scenes} scenes to: {script_output_path}")
            self.logger.info(f"  Total script length: {len(full_script)} characters")
            return True, None

        error_msg = f"Failed to write script to: {script_output_path}"
        self.logger.error(error_msg)
        return False, error_msg

    def _add_scene_indices(self) -> Tuple[bool, Optional[str]]:
        source_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)

        if not self.file_io.exists(source_file):
            error_msg = f"Direction source file does not exist: {source_file}"
            self.logger.error(error_msg)
            return False, error_msg

        direction_data = self.file_io.read_json(source_file)

        if not direction_data or 'scenes' not in direction_data:
            error_msg = "Invalid direction data: missing 'scenes' array"
            self.logger.error(error_msg)
            return False, error_msg

        updated_scenes = []
        for index, scene in enumerate(direction_data['scenes']):
            updated_scene = {'sceneIndex': index, **scene}
            updated_scenes.append(updated_scene)
        direction_data['scenes'] = updated_scenes

        success = self.file_io.write_json(source_file, direction_data)

        if success:
            self.logger.info(f"Added sceneIndex to {len(direction_data['scenes'])} scenes")
            return True, None

        error_msg = f"Failed to write scene indices to: {source_file}"
        self.logger.error(error_msg)
        return False, error_msg

    @try_catch(return_on_error=(False, "Direction post-processing failed due to an unexpected error"))
    async def process(self) -> Tuple[bool, Optional[str]]:
        self.logger.info("Processing video direction output")

        success, error_msg = self._add_scene_indices()
        if not success:
            self.logger.error(f"Failed to add scene indices: {error_msg}")
            return False, error_msg

        success, error_msg = self._extract_script_from_direction()
        if not success:
            self.logger.error(f"Failed to extract script from direction: {error_msg}")
            return False, error_msg

        file_path, version = self.write_versioned_output()
        if not version or not file_path:
            error_msg = "Failed to write versioned output for direction"
            self.logger.error(error_msg)
            return False, error_msg

        self.logger.info("Video direction output processed successfully")
        return True, file_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post-process video direction")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging (default: True)')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    set_console_logging(args.log)

    post_processor = VideoDirectionPostProcessing(topic=args.topic)

    success, file_path = asyncio.run(post_processor.run())

    if success and file_path:
        post_processor.logger.info("Successfully processed video direction")
        post_processor.logger.info("Output file: {file_path}")
    else:
        post_processor.logger.error("Failed to process video direction")
        sys.exit(1)

    post_processor.logger.info("Video direction post-processing completed successfully")