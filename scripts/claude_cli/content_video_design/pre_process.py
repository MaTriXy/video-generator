import json
import sys
import os
import glob
from typing import Dict, Any, List
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.base_pre_process import BasePreProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController
from scripts.transcript_to_string import convert_transcript_to_string


class VideoDesignPreProcess(BasePreProcess):

    def __init__(self, topic: str):
        super().__init__(
            asset_type=AssetType.DESIGN,
            logger_name='VideoDesignPreProcess',
            log_file_name='content-video-design-pre-process',
            topic=topic,
        )

        self.metadata_controller = VideoStepMetadataController()
        self.video_direction = {}
        self.asset_manifest = {}

    @try_catch
    def get_audio_transcript(self) -> list:
        try:
            transcript_data = self.output_controller.read_output(AssetType.TRANSCRIPT)
            return transcript_data
        except Exception as e:
            self.logger.error(f"Error loading audio transcript: {str(e)}")
            return []

    @try_catch
    def get_scene_transcript(self, transcript: List[Dict[str, Any]], scene_index: int) -> str:
        scenes = self.video_direction.get('scenes', [])

        if scene_index >= len(scenes):
            self.logger.warning(f"Scene index {scene_index} out of range. Total scenes: {len(scenes)}")
            return ""

        scene = scenes[scene_index]
        scene_start_ms = scene.get('sceneStartTime') or scene.get('startTime', 0)
        scene_end_ms = scene.get('sceneEndTime') or scene.get('endTime', 0)
        scene_transcript = []

        for word_data in transcript:
            word_start = word_data.get('start_ms', 0)
            word_end = word_data.get('end_ms', 0)

            # Check if word falls within scene boundaries
            if word_start >= scene_start_ms and word_end <= scene_end_ms:
                # Create new entry with scene-relative timing
                scene_relative_word = {
                    'word': word_data.get('word', ''),
                    'start_ms': word_start - scene_start_ms,  # Make relative to scene start
                    'end_ms': word_end - scene_start_ms
                }
                scene_transcript.append(scene_relative_word)

        flat_list = [str(value) for item in scene_transcript for value in (item['word'], item['start_ms'], item['end_ms'])]
        scene_transcript_string = ", ".join(flat_list)
        return scene_transcript_string

    @try_catch
    def save_prompt(self):
        self.video_direction = self.output_controller.read_output(AssetType.DIRECTION)
        self.logger.info(f"Video direction: read")
        if not self.video_direction:
            raise ValueError("No video direction found")

        self.asset_manifest = self.output_controller.read_output(AssetType.ASSETS)
        self.logger.info(f"Asset manifest: read")

        full_transcript = self.get_audio_transcript()
        self.logger.info(f"Full transcript: {full_transcript}")

        total_scenes = len(self.video_direction.get('scenes', []))
        for scene_index in range(total_scenes):
            variables = self.build_prompt_variables(
                scene_index=scene_index,
                full_transcript=full_transcript,
            )
            prompt = self.build_prompt(
                variables=variables,
            )
            file_path = self.prompt_path.replace("[scene_index]", str(scene_index))
            self.save_prompt_to_file(prompt, scene_index=scene_index)
            self.logger.info(f" Saved video design prompt to: {file_path.format(scene_index=scene_index)}")

        output = {
            "total_scenes": total_scenes
        }
        self.metadata_controller.write(self.asset_type, output)

    @try_catch
    def get_scene_direction(self, scene_index: int) -> Dict[str, Any]:
        scenes = self.video_direction.get('scenes', [])

        if not scenes:
            raise ValueError("No scenes found in video_direction")

        # Check if scene_index is valid
        if scene_index >= len(scenes):
            raise ValueError(f"Scene index {scene_index} out of range. Total scenes: {len(scenes)}")

        # Get the specific scene
        scene = scenes[scene_index]

        self.logger.info(f"Retrieved scene {scene_index} from video_direction")

        return scene

    @try_catch
    def build_prompt_variables(
        self,
        scene_index: int,
        full_transcript: list = None,
    ) -> Dict[str, Any]:
        scene_direction = self.get_scene_direction(scene_index)
        course_metadata = self.get_metadata()

        # Get scene-specific transcript with relative timings
        scene_start_ms = scene_direction.get("sceneStartTime", 0)
        scene_end_ms = scene_direction.get("sceneEndTime", 0)

        scene_transcript_string = self.get_scene_transcript(full_transcript, scene_index)

        # Format asset manifest as a string for the prompt
        asset_manifest_string = json.dumps(self.asset_manifest, indent=2) if self.asset_manifest else "No assets available"

        variables = {
            **course_metadata,
            "scene_index": scene_direction.get("scene", 0),
            "scene_startTime": scene_start_ms,
            "scene_endTime": scene_end_ms,
            "scene_audio_transcript": scene_direction.get("audioTranscriptPortion", ""),
            "direction_video_description": scene_direction.get("videoDescription", ""),
            "scene_direction_json": scene_direction,
            "audio_transcript_with_timings": scene_transcript_string,
            "asset_manifest": asset_manifest_string
        }

        self.logger.info(f"Built prompt variables for scene {scene_index}: {list(variables.keys())}")

        return variables


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-process video design prompt")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    args = parser.parse_args()

    pre_process = VideoDesignPreProcess(topic=args.topic)
    pre_process.run()

    metadata = pre_process.metadata_controller.read(AssetType.DESIGN)

    pre_process.logger.info("=" * 80)
    pre_process.logger.info("Pre-processing completed successfully")
    pre_process.logger.info(f"Total scene designs to generate: {metadata['total_scenes']}")
    pre_process.logger.info("=" * 80)
