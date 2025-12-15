import sys
import os
from typing import Optional, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig, AssetType
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.logging_config import set_console_logging
from scripts.claude_cli.content_video_direction.scene_timestamp_calculator import match_narration_to_transcript


class VideoDirectionPostProcessing(BasePostProcess):

    def __init__(self, topic: str):
        super().__init__(
            logger_name='VideoDirectionPostProcessing',
            log_file_name='content-video-direction-post-process',
            topic=topic,
            asset_type=AssetType.DIRECTION,
        )

    @try_catch
    def _calculate_timestamps(self) -> bool:
        """
        Calculate startTime/endTime for each scene by matching narration to transcript.
        This runs before scene indices are added.
        """
        source_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)

        if not self.file_io.exists(source_file):
            self.logger.error(f"Source file does not exist: {source_file}")
            return False

        direction_data = self.file_io.read_json(source_file)

        if not direction_data or 'scenes' not in direction_data:
            self.logger.error("Invalid direction data: missing 'scenes' array")
            return False

        # Read transcript
        self.logger.info("Reading transcript for timestamp calculation")
        transcript = self.output_controller.read_output(AssetType.TRANSCRIPT)

        if not transcript:
            self.logger.error("No transcript found - cannot calculate timestamps")
            return False

        self.logger.info(f"Transcript loaded: {len(transcript)} words")

        # Match each scene's narration to transcript sequentially
        transcript_index = 0
        total_scenes = len(direction_data['scenes'])

        for scene_idx, scene in enumerate(direction_data['scenes']):
            narration = scene.get('audioTranscriptPortion', '')

            if not narration:
                self.logger.warning(f"Scene {scene_idx + 1}: No audioTranscriptPortion text found")
                continue

            self.logger.info(f"Scene {scene_idx + 1}/{total_scenes}: Matching narration ({len(narration)} chars)")

            # Match narration to transcript
            start_ms, end_ms, next_index, matched_count, total_words = match_narration_to_transcript(
                narration, transcript, transcript_index
            )

            if start_ms is None or end_ms is None:
                self.logger.error(f"Scene {scene_idx + 1}: Failed to match narration to transcript")
                return False

            scene['sceneStartTime'] = start_ms
            scene['sceneEndTime'] = end_ms

            # Update transcript index for next scene
            transcript_index = next_index

            match_percentage = (matched_count / total_words * 100) if total_words > 0 else 0
            self.logger.info(
                f"Scene {scene_idx + 1}: {start_ms}ms - {end_ms}ms "
                f"({matched_count}/{total_words} words matched = {match_percentage:.1f}%)"
            )

        # Write back the modified data
        success = self.file_io.write_json(source_file, direction_data)

        if success:
            self.logger.info(f"✓ Calculated timestamps for {total_scenes} scenes")

        return success

    @try_catch
    def _add_scene_indices(self) -> bool:
        """Add sceneIndex to each scene object in the direction output."""
        source_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)

        if not self.file_io.exists(source_file):
            self.logger.error(f"Source file does not exist: {source_file}")
            return False

        direction_data = self.file_io.read_json(source_file)

        if not direction_data or 'scenes' not in direction_data:
            self.logger.error("Invalid direction data: missing 'scenes' array")
            return False

        # Add sceneIndex as the first field in each scene
        updated_scenes = []
        for index, scene in enumerate(direction_data['scenes']):
            updated_scene = {'sceneIndex': index, **scene}
            updated_scenes.append(updated_scene)
        direction_data['scenes'] = updated_scenes

        # Write back the modified data
        success = self.file_io.write_json(source_file, direction_data)

        if success:
            self.logger.info(f"Added sceneIndex to {len(direction_data['scenes'])} scenes")

        return success

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[str]]:
        self.logger.info("Processing video direction output")

        # Calculate timestamps from narration + transcript
        if not self._calculate_timestamps():
            self.logger.error("Failed to calculate timestamps")
            return None, None

        # Add scene indices after timestamps are calculated
        if not self._add_scene_indices():
            self.logger.error("Failed to add scene indices")
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