import sys
import os
import asyncio
import random
from typing import Optional, Tuple
from pathlib import Path


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.utility.config import MAPBOX_TOKENS
from scripts.logging_config import set_console_logging
from scripts.enums import AssetType
from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController


FPS = 30
TEMPLATE_PATH = Path(__file__).parent / "composition_template.txt"


def generate_remotion_composition(scenes_data: list) -> str:
    """Generate a Remotion Composition.tsx using Series for scene playback.

    Reads composition_template.txt and replaces placeholders:
      - {{SCENE_IMPORTS}}: import SceneN from "./scene_N" lines
      - {{SERIES_SEQUENCES}}: Series.Sequence blocks for each scene
      - {{MAPBOX_TOKEN}}: a Mapbox token (if configured)
    """
    template = TEMPLATE_PATH.read_text(encoding='utf-8')

    scene_imports = '\n'.join(
        f'import Scene{s["index"]} from "./scene_{s["index"]}";'
        for s in scenes_data
    )

    series_lines = []
    for scene in scenes_data:
        idx = scene['index']
        dur = scene['duration_frames']
        series_lines.append(f'        <Series.Sequence durationInFrames={{{dur}}}>')
        series_lines.append(f'          <Scene{idx} Arrow={{Arrow}} Text={{Text}} seededRandom={{seededRandom}} mapboxToken={{MAPBOX_TOKEN}} />')
        series_lines.append(f'        </Series.Sequence>')
    series_sequences = '\n'.join(series_lines)

    tokens = [t.strip() for t in MAPBOX_TOKENS.split(',') if t.strip()]
    mapbox_token = random.choice(tokens) if tokens else ""

    result = template.replace('{{MAPBOX_TOKEN}}', mapbox_token)
    result = result.replace('{{SCENE_IMPORTS}}', scene_imports)
    result = result.replace('{{SERIES_SEQUENCES}}', series_sequences)

    return result


class VideoContentPostProcessing(BasePostProcess):
    """
    Post-processing for Remotion video component generation.
    Generates a Remotion Composition file from the scene files and direction timings.
    """

    def __init__(self, topic: str):
        super().__init__(
            logger_name='ContentVideoPostProcessing',
            log_file_name='content-video-post-process',
            topic=topic,
            asset_type=AssetType.VIDEO,
        )
        self.claude_cli_scene_output_path = self.claude_cli_config.get_latest_path(self.asset_type)
        self.metadata_controller = VideoStepMetadataController(topic)

    @try_catch
    def copy_scene_files_to_version_dir(self, version_dir: Path) -> bool:
        self.logger.info(f"Copying scene files to {version_dir}")

        latest_path = self.claude_cli_config.get_latest_path(self.asset_type)
        base_dir = Path(latest_path).parent
        pattern = "scene_[0-9]*.tsx"
        scene_files = list(base_dir.glob(pattern))

        if not scene_files:
            self.logger.warning(f"No scene files found matching pattern: {pattern}")
            return False

        self.logger.info(f"Found {len(scene_files)} scene files to copy")

        copied_count = 0
        for scene_file in scene_files:
            try:
                dest_file = version_dir / scene_file.name
                dest_file.write_text(scene_file.read_text(encoding='utf-8'), encoding='utf-8')
                copied_count += 1
            except Exception as e:
                self.logger.error(f"Failed to copy {scene_file.name}: {e}")

        self.logger.info(f"Copied {copied_count}/{len(scene_files)} scene files to {version_dir}")
        return copied_count == len(scene_files)

    @try_catch
    def generate_from_direction_file(self) -> Optional[str]:
        self.logger.info("Generating Remotion Composition from direction file")

        direction_data = self.output_controller.read_output(AssetType.DIRECTION)
        max_scenes = self.metadata_controller.get_total_scenes(self.asset_type)
        if not direction_data:
            self.logger.error("Could not read direction file")
            return None

        scenes = direction_data.get('scenes', [])
        scenes_data = []
        scene_durations = []

        for scene_index, scene in enumerate(scenes):
            if scene_index >= max_scenes:
                break

            start_ms = scene.get('sceneStartTime', scene.get('startTime', 0))
            end_ms = scene.get('sceneEndTime', scene.get('endTime', 0))
            end_f = scene.get('sceneEndFrame', 0)
            start_f = scene.get('sceneStartFrame', 0)
            duration_frames = end_f - start_f
            scenes_data.append({
                'index': scene_index,
                'start_time': start_ms,
                'end_time': end_ms,
                'duration_frames': duration_frames,
            })
            scene_durations.append(duration_frames)

        self.logger.info(f"----> Found {len(scenes_data)} scenes in direction file")

        total_duration = sum(scene_durations)

        self.gen_metadata_controller.set_metadata({
            "scene_durations": scene_durations,
            "total_duration_frames": total_duration,
            "fps": FPS,
        })

        composition_content = generate_remotion_composition(scenes_data)

        self.logger.info(f"Generated Remotion Composition with {len(scenes_data)} scenes, {total_duration} total frames")
        return composition_content

    @try_catch
    def process_output(self) -> Tuple[Optional[str], Optional[str]]:
        self.logger.info("Processing video output")
        file_path, version = self.write_versioned_output()

        if file_path and version:
            version_dir = Path(file_path).parent
            self.copy_scene_files_to_version_dir(version_dir)

        return version, file_path

    def generate_and_save_from_direction(self) -> Tuple[bool, Optional[str]]:
        composition_content = self.generate_from_direction_file()

        if not composition_content:
            error_msg = "Failed to generate Remotion Composition from direction file - no content generated"
            self.logger.error(error_msg)
            return False, error_msg

        latest_path = self.claude_cli_config.get_latest_path(self.asset_type)
        composition_path = str(Path(latest_path).parent / "composition.tsx")

        try:
            self.file_io.write_text(latest_path, composition_content)
            self.file_io.write_text(composition_path, composition_content)
            self.logger.info(f"Composition file saved to: {composition_path}")

            version, file_path = self.process_output()

            if not version or not file_path:
                error_msg = "Failed to process and version the Composition output"
                self.logger.error(error_msg)
                return False, error_msg

            self.logger.info(f"Composition processed and saved as {version}: {file_path}")
            return True, file_path
        except Exception as e:
            error_msg = f"Failed to save and process Composition file: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def validate_output(self) -> bool:
        self.logger.info("Validating video output...")

        total_scenes = self.metadata_controller.get_total_scenes(self.asset_type)
        if total_scenes == 0:
            self.logger.error("No scenes found in metadata (total_scenes is 0)")
            return False

        self.gen_metadata_controller.set_metadata({"total_scenes": total_scenes})
        self.logger.info(f"Expecting {total_scenes} scenes (0 to {total_scenes - 1})")

        latest_path_template = self.claude_cli_scene_output_path
        latest_folder = Path(latest_path_template).parent

        missing_scenes = []
        existing_scenes = []

        for scene_index in range(total_scenes):
            scene_file_path = latest_folder / f"scene_{scene_index}.tsx"
            if scene_file_path.exists():
                existing_scenes.append(scene_index)
            else:
                missing_scenes.append(scene_index)

        self.logger.info(f"Found {len(existing_scenes)}/{total_scenes} scene files")

        if missing_scenes:
            missing_scenes_str = ', '.join(str(s) for s in missing_scenes)
            sys.stderr.write(f"Missing scenes: [{missing_scenes_str}]\n")
            sys.stderr.write(f"Regenerate these scenes: {missing_scenes_str}\n")
            return False

        self.logger.info("All scene files are present")
        return True

    async def process(self) -> Tuple[bool, Optional[str]]:
        if not self.validate_output():
            error_msg = "Video output validation failed - missing scene files"
            self.logger.error(error_msg)
            return False, error_msg

        success, file_path = self.generate_and_save_from_direction()
        if not success or not file_path:
            error_msg = "Failed to generate and save Remotion Composition from direction file"
            self.logger.error(error_msg)
            return False, error_msg
        return True, file_path

    async def run(self) -> Tuple[bool, Optional[str]]:
        self.gen_metadata_controller.set_metadata({"type": "claude_cli"})
        result = await self.process()
        self.gen_metadata_controller.save_metadata()
        return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post-process Remotion video component")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--log', action='store_true', default=True)
    parser.add_argument('--no-log', action='store_false', dest='log')
    args = parser.parse_args()

    set_console_logging(args.log)

    post_processor = VideoContentPostProcessing(topic=args.topic)

    success, file_path = asyncio.run(post_processor.run())
    if success and file_path:
        post_processor.logger.info(f"Successfully generated Remotion Composition at {file_path}")
    else:
        post_processor.logger.error("Failed to generate Remotion Composition")
        sys.exit(1)
