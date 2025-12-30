import sys
import os
from pathlib import Path
from typing import Optional, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig, AssetType
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

    @try_catch
    def _extract_script_from_direction(self) -> bool:
        source_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)

        if not self.file_io.exists(source_file):
            self.logger.error(f"Source file does not exist: {source_file}")
            return False

        direction_data = self.file_io.read_json(source_file)

        if not direction_data or 'scenes' not in direction_data:
            self.logger.error("Invalid direction data: missing 'scenes' array")
            return False

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
            self.logger.error("No audioTranscriptPortion found in any scene")
            return False

        full_script = "\n\n".join(script_parts)

        script_output_path = self.claude_cli_config.get_final_path(AssetType.SCRIPT)
        Path(script_output_path).parent.mkdir(parents=True, exist_ok=True)

        success = self.file_io.write_text(script_output_path, full_script)

        if success:
            self.logger.info(f"✓ Extracted script from {total_scenes} scenes to: {script_output_path}")
            self.logger.info(f"  Total script length: {len(full_script)} characters")

        return success

    @try_catch
    def _add_scene_indices(self) -> bool:
        source_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)

        if not self.file_io.exists(source_file):
            self.logger.error(f"Source file does not exist: {source_file}")
            return False

        direction_data = self.file_io.read_json(source_file)

        if not direction_data or 'scenes' not in direction_data:
            self.logger.error("Invalid direction data: missing 'scenes' array")
            return False

        updated_scenes = []
        for index, scene in enumerate(direction_data['scenes']):
            updated_scene = {'sceneIndex': index, **scene}
            updated_scenes.append(updated_scene)
        direction_data['scenes'] = updated_scenes

        success = self.file_io.write_json(source_file, direction_data)

        if success:
            self.logger.info(f"Added sceneIndex to {len(direction_data['scenes'])} scenes")

        return success

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[str]]:
        self.logger.info("Processing video direction output")

        if not self._add_scene_indices():
            self.logger.error("Failed to add scene indices")
            return None, None

        if not self._extract_script_from_direction():
            self.logger.error("Failed to extract script from direction")
            return None, None

        file_path, version = self.write_versioned_output()
        self.logger.info("Video direction output processed successfully")
        return version, file_path

    @try_catch
    def process(self) -> Tuple[bool, Optional[str]]:
        version, file_path = self.process_output()

        if not version or not file_path:
            self.logger.error("Failed to process video direction output")
            return False, None

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

    success, file_path = post_processor.run()

    if success and file_path:
        post_processor.logger.info("Successfully processed video direction")
        post_processor.logger.info("Output file: {file_path}")
    else:
        post_processor.logger.error("Failed to process video direction")
        sys.exit(1)

    post_processor.logger.info("Video direction post-processing completed successfully")