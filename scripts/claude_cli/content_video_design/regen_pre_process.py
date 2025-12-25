import json
import sys
import os
from typing import List
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.content_video_design.pre_process import VideoDesignPreProcess
from scripts.controllers.utils.decorators.try_catch import try_catch


class VideoDesignRegenPreProcess(VideoDesignPreProcess):

    def __init__(self, topic: str, scenes: List[int]):
        super().__init__(topic=topic)
        self.scenes = scenes
        self.logger.info(f"Initialized regeneration for scenes: {scenes}")

    @try_catch
    def delete_scene_files(self, scene_indices: List[int]):
        path_template = self.claude_cli_config.get_latest_path(self.asset_type)
        for scene_index in scene_indices:
            file_path = path_template.format(scene_index=scene_index)
            try:
                self.file_io.delete_file(file_path)
                self.logger.info(f"Deleted: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to delete {file_path}: {str(e)}")

    @try_catch
    def delete_scene_prompts(self, scene_indices: List[int]):
        for scene_index in scene_indices:
            file_path = self.prompt_path.format(scene_index=scene_index)
            try:
                self.file_io.delete_file(file_path)
                self.logger.info(f"Deleted prompt: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to delete prompt {file_path}: {str(e)}")

    @try_catch
    def save_prompt(self):
        self.video_direction = self.output_controller.read_output(AssetType.DIRECTION)
        self.logger.info(f"Video direction: read")
        if not self.video_direction:
            raise ValueError("No video direction found")

        self.asset_manifest = self.output_controller.read_output(AssetType.ASSETS)
        self.logger.info(f"Asset manifest: read")

        full_transcript = self.get_audio_transcript()
        self.logger.info(f"Full transcript: read")

        for scene_index in self.scenes:
            variables = self.build_prompt_variables(
                scene_index=scene_index,
                full_transcript=full_transcript,
            )
            prompt = self.build_prompt(variables=variables)
            self.save_prompt_to_file(prompt, scene_index=scene_index)
            file_path = self.prompt_path.format(scene_index=scene_index)
            self.logger.info(f"Saved video design prompt to: {file_path}")

    def run(self):
        self.delete_scene_files(self.scenes)
        self.delete_scene_prompts(self.scenes)
        self.logger.info(f"Deleted existing outputs for scenes: {self.scenes}")
        self.save_prompt()
        self.logger.info(f"Saved prompts for scenes: {self.scenes}")
        self.logger.info(f"Completed pre-processing for scenes: {self.scenes}")
        self.gen_metadata_controller.save_metadata()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Regenerate pre-process for specific scenes")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--scenes', type=str, required=True, help='Comma-separated scene indices (e.g., "0,2,3")')
    args = parser.parse_args()

    scene_indices = [int(s.strip()) for s in args.scenes.split(',')]

    pre_process = VideoDesignRegenPreProcess(topic=args.topic, scenes=scene_indices)
    pre_process.run()

    pre_process.logger.info("=" * 80)
    pre_process.logger.info("Regeneration pre-processing completed successfully")
    pre_process.logger.info(f"Regenerated scenes: {scene_indices}")
    pre_process.logger.info("=" * 80)
