"""
Scene Pre-Process - Handles prompt variable preparation for individual scene generation.
"""

import json
import math
from datetime import datetime
from math import ceil
import sys
import os
from typing import Dict, Any, List, Tuple
from pathlib import Path

import tiktoken


# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.base_pre_process import BasePreProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController


class VideoPreProcess(BasePreProcess):

    def __init__(self, topic: str, max_scenes: int = None, gen_prompt: bool = True):
        super().__init__(
            asset_type=AssetType.VIDEO,
            logger_name='VideoScenePreProcess',
            log_file_name='content-video-pre-process',
            topic=topic,
            gen_prompt=gen_prompt,
        )

        self.metadata_controller = VideoStepMetadataController(topic)
        self.video_direction = {}
        self.asset_manifest = {}
        self.transcript = []
        self.total_frames = 0
        self.max_scenes = max_scenes
        self._batch_prompt_paths: List[str] = []

        self.FPS = 30
        self.MAX_SCENES_PER_SUBAGENT = 10
        self.TOKEN_LIMIT = 23_000
        self._tiktoken_enc = tiktoken.get_encoding("cl100k_base")

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
        # Use visual start frame (sceneStartFrame) as reference so transcript
        # frame numbers align with Remotion's useCurrentFrame() in Series
        scene_start_frame = scene.get('sceneStartFrame', 0)
        scene_transcript = []

        for word_data in transcript:
            word_start = word_data.get('start_ms', 0)
            word_end = word_data.get('end_ms', 0)

            # Check if word falls within scene boundaries
            if word_start >= scene_start_ms and word_end <= scene_end_ms:
                absolute_frame = round(word_start / 1000 * self.FPS)
                start_frame = absolute_frame - scene_start_frame
                scene_relative_word = {
                    'word': word_data.get('word', ''),
                    'start_frame': start_frame,
                }
                scene_transcript.append(scene_relative_word)

        flat_list = [str(value) for item in scene_transcript for value in (item['word'], item['start_frame'])]
        scene_transcript_string = ", ".join(flat_list)
        return scene_transcript_string

    def _calculate_scene_batches(self, total_scenes: int) -> List[List[int]]:
        """Distribute scenes evenly across subagents. Each subagent gets max MAX_SCENES_PER_SUBAGENT scenes."""
        if total_scenes <= self.MAX_SCENES_PER_SUBAGENT:
            return [list(range(total_scenes))]

        num_subagents = math.ceil(total_scenes / self.MAX_SCENES_PER_SUBAGENT)
        base = total_scenes // num_subagents
        remainder = total_scenes % num_subagents

        batches = []
        idx = 0
        for i in range(num_subagents):
            size = base + (1 if i < remainder else 0)
            batches.append(list(range(idx, idx + size)))
            idx += size

        return batches

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken's cl100k_base encoding."""
        return len(self._tiktoken_enc.encode(text))

    def _build_combined_prompt(
        self,
        batch: List[int],
        scene_prompts: Dict[int, str],
        scene_assets: List[List[Dict[str, Any]]],
        scene_audio_effects: List[List[Dict[str, Any]]],
        shared_header: str,
    ) -> str:
        """Assemble the full prompt string for a batch of scenes."""
        combined_parts = []
        for scene_index in batch:
            combined_parts.append(f"# Scene {scene_index}\n\n{scene_prompts[scene_index]}")
        scenes_section = "\n\n---\n\n".join(combined_parts)

        seen_asset_names = set()
        batch_assets = []
        for scene_index in batch:
            for asset in scene_assets[scene_index]:
                name = asset.get("name")
                if name and name not in seen_asset_names:
                    seen_asset_names.add(name)
                    batch_assets.append(asset)

        asset_manifest_json = json.dumps(batch_assets, indent=2) if batch_assets else "[]"
        asset_footer = f"<asset_manifest>{asset_manifest_json}</asset_manifest>"

        seen_effect_names = set()
        batch_effects = []
        for scene_index in batch:
            for effect in scene_audio_effects[scene_index]:
                name = effect.get("name")
                if name and name not in seen_effect_names:
                    seen_effect_names.add(name)
                    batch_effects.append(effect)

        footer = asset_footer
        if batch_effects:
            audio_effects_json = json.dumps(batch_effects, indent=2)
            footer += f"\n\n<audio_effects_manifest>{audio_effects_json}</audio_effects_manifest>"

        return f"{shared_header}\n\n---\n\n{scenes_section}\n\n---\n\n{footer}"

    def _split_batch_by_tokens(
        self,
        batch: List[int],
        scene_prompts: Dict[int, str],
        scene_assets: List[List[Dict[str, Any]]],
        scene_audio_effects: List[List[Dict[str, Any]]],
        shared_header: str,
    ) -> List[Tuple[List[int], str, int]]:
        """Recursively split a batch until each sub-batch's prompt is under TOKEN_LIMIT."""
        combined_prompt = self._build_combined_prompt(batch, scene_prompts, scene_assets, scene_audio_effects, shared_header)
        token_count = self._count_tokens(combined_prompt)

        if token_count <= self.TOKEN_LIMIT:
            return [(batch, combined_prompt, token_count)]

        if len(batch) <= 1:
            self.logger.warning(f"Scene {batch[0]} exceeds token limit: {token_count} tokens (limit {self.TOKEN_LIMIT})")
            return [(batch, combined_prompt, token_count)]

        self.logger.info(f"Batch scenes {batch[0]}-{batch[-1]} has {token_count} tokens (limit {self.TOKEN_LIMIT}), splitting")
        mid = len(batch) // 2
        left = self._split_batch_by_tokens(batch[:mid], scene_prompts, scene_assets, scene_audio_effects, shared_header)
        right = self._split_batch_by_tokens(batch[mid:], scene_prompts, scene_assets, scene_audio_effects, shared_header)
        return left + right

    def save_prompt(self):
        self.video_direction = self.output_controller.read_output(AssetType.DIRECTION)
        if not self.video_direction:
            raise ValueError("No video direction found. Direction step may not have completed.")
        scenes = self.video_direction.get('scenes', [])
        if not scenes:
            raise ValueError("Video direction has no scenes.")
        for i, scene in enumerate(scenes):
            if 'videoDescription' not in scene:
                raise ValueError(f"Scene {i} missing 'videoDescription' in direction.")
        self.logger.info(f"Video direction: read ({len(scenes)} scenes)")

        self.asset_manifest = self.output_controller.read_output(AssetType.ASSETS)
        if not self.asset_manifest:
            raise ValueError("No asset manifest found. Assets step may not have completed.")
        self.logger.info(f"Asset manifest: read")

        self.transcript = self.get_audio_transcript()
        self.logger.info(f"Audio transcript: {len(self.transcript)} words")

        scenes = self.video_direction.get('scenes', [])
        total_scenes = len(scenes)
        if self.max_scenes and total_scenes > self.max_scenes:
            total_scenes = self.max_scenes

        # Calculate frame numbers for each scene and write to direction JSON
        last_end_frame = 0
        for i, scene in enumerate(scenes):
            start_ms = scene.get('sceneStartTime', 0)
            end_ms = scene.get('sceneEndTime', 0)
            scene['sceneStartFrame'] = 0 if i == 0 else last_end_frame
            scene['sceneEndFrame'] = ceil(end_ms / 1000 * self.FPS) + 8
            if i == len(scenes) - 1:
                scene['sceneEndFrame'] += 20
            last_end_frame = scene['sceneEndFrame']

        # Ensure total frames covers the full audio transcript
        if self.transcript:
            last_word_end_ms = max(w.get('end_ms', 0) for w in self.transcript)
            audio_end_frame = ceil(last_word_end_ms / 1000 * self.FPS) + 60
            if last_end_frame < audio_end_frame:
                self.logger.info(f"Extending last scene to cover full audio: {last_end_frame} -> {audio_end_frame} frames (audio ends at {last_word_end_ms}ms)")
                scenes[-1]['sceneEndFrame'] = audio_end_frame
                last_end_frame = audio_end_frame

        self.video_direction['totalFrames'] = last_end_frame
        self.total_frames = last_end_frame
        self.manifest_controller.update_metadata('totalFrames', last_end_frame)
        self.manifest_controller.update_metadata('totalScenes', total_scenes)
        self.logger.info(f"Calculated frames at {self.FPS}fps: totalFrames={last_end_frame}, totalScenes={total_scenes}")

        # Write updated direction JSON back to latest and versioned paths
        direction_latest_path = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)
        self.file_io.write_json(direction_latest_path, self.video_direction)

        direction_manifest = self.manifest_controller.get_field(AssetType.DIRECTION)
        if direction_manifest and direction_manifest.get('path'):
            self.file_io.write_json(direction_manifest['path'], self.video_direction)
        self.logger.info(f"Updated direction JSON with frame data")

        course_metadata = self.get_metadata()

        batches = self._calculate_scene_batches(total_scenes)
        self.logger.info(f"Batching {total_scenes} scenes into {len(batches)} prompt(s): {[len(b) for b in batches]} scenes each")

        # Build per-scene prompts and collect assets + audio effects
        scene_prompts = {}
        scene_assets = []
        scene_audio_effects = []
        artstyle_json = self.load_artstyle("code")
        artstyle_content = f"<artstyle>{artstyle_json}</artstyle>"
        for scene_index in range(total_scenes):
            variables = self.build_prompt_variables(scene_index=scene_index)
            prompt = self.build_prompt(variables=variables, append_date=False)

            scene_prompts[scene_index] = f"<video_id>{self.video_id}</video_id>\n<scene_index>{scene_index}</scene_index>\n\n{prompt}"

            # Collect assets and audio effects for this scene
            scene_direction = self.get_scene_direction(scene_index)

            asset_names = self.get_scene_asset_names(scene_direction)
            filtered_assets = self.get_filtered_asset_manifest(asset_names)
            scene_assets.append(filtered_assets)

            effect_names = self.get_scene_audio_effect_names(scene_direction)
            filtered_effects = self.get_filtered_audio_effects(effect_names)
            scene_audio_effects.append(filtered_effects)

        prompts_dir = Path(project_root) / "Outputs" / self.claude_cli_config.topic / "Video" / "Prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        shared_header = (
            f"<video_aspect_ratio>{course_metadata.get('video_ratio', '')}</video_aspect_ratio>\n"
            f"<viewport_width>{course_metadata.get('viewport_width', '')}</viewport_width>\n"
            f"<viewport_height>{course_metadata.get('viewport_height', '')}</viewport_height>"
            f"{artstyle_content}\n"
        )

        # Split batches by token count so no prompt exceeds TOKEN_LIMIT
        final_batches: List[Tuple[List[int], str, int]] = []
        for batch in batches:
            final_batches.extend(self._split_batch_by_tokens(batch, scene_prompts, scene_assets, scene_audio_effects, shared_header))

        self.logger.info(f"After token-aware splitting: {len(final_batches)} prompt(s) from {len(batches)} initial batch(es)")

        self._batch_prompt_paths = []
        for batch, combined_prompt, token_count in final_batches:
            batch_start = batch[0]
            batch_end = batch[-1]

            # Save batch prompt file
            prompt_filename = f"prompt_{batch_start}_{batch_end}.md"
            prompt_path = prompts_dir / prompt_filename
            original_path = prompt_path.with_stem(prompt_path.stem + "_original")

            self.file_io.write_text(str(original_path), combined_prompt)
            truncated_prompt = ' '.join(combined_prompt.split())
            self.file_io.write_text(str(prompt_path), truncated_prompt)

            self._batch_prompt_paths.append(str(prompt_path.resolve()))
            self.logger.info(f"Saved batch prompt: {prompt_filename} (scenes {batch_start}-{batch_end}, {token_count} tokens)")

        output = {
            "total_scenes": total_scenes
        }
        self.metadata_controller.write(self.asset_type, output)

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
    def get_scene_asset_names(self, scene_direction: Dict[str, Any]) -> List[str]:
        """Extract asset names referenced in the scene's videoDescription by matching against required_assets."""
        video_description = scene_direction.get('videoDescription', '')
        video_description = video_description.lower()
        required_assets = self.asset_manifest.get('assets', [])
        asset_names = []
        for asset in required_assets:
            name = asset['name']
            if name and f'@{name.lower()}' in video_description:
                asset_names.append(name)
        return asset_names

    @try_catch
    def get_scene_audio_effect_names(self, scene_direction: Dict[str, Any]) -> List[str]:
        """Extract audio effect names referenced in the scene's videoDescription using $effectname pattern."""
        video_description = scene_direction.get('videoDescription', '')
        video_description_lower = video_description.lower()
        audio_effects = self.video_direction.get('required_audio_effects', [])
        effect_names = []
        for effect in audio_effects:
            name = effect.get('name', '')
            if name and f'${name.lower()}' in video_description_lower:
                effect_names.append(name)
        return effect_names

    @try_catch
    def get_filtered_audio_effects(self, effect_names: List[str]) -> List[Dict[str, Any]]:
        """Filter direction's required_audio_effects to only include effects used in the scene."""
        audio_effects = self.video_direction.get('required_audio_effects', [])
        filtered = []
        for effect in audio_effects:
            if effect.get('name') in effect_names and effect.get('url'):
                filtered.append({
                    "name": effect['name'],
                    "url": effect['url'],
                    "duration": effect.get('duration'),
                })
        return filtered

    @try_catch
    def get_filtered_asset_manifest(self, asset_names: List[str]) -> List[Dict[str, Any]]:
        """Filter asset manifest to only include assets used in the scene and add svg_content."""
        filtered_assets = []
        assets_list = self.asset_manifest.get('assets', [])

        for asset in assets_list:
            asset_name = asset.get('name')
            if asset_name in asset_names:
                filtered_asset = {
                    "name": asset_name,
                    "aspect_ratio": asset.get('aspect_ratio', '1:1'),
                    "composition": asset.get('composition', ''),
                }

                if asset.get('url'):
                    filtered_asset["assetUrl"] = asset['url']
                else:
                    asset_path = Path(project_root) / asset.get('path')
                    filtered_asset["svg_content"] = self.file_io.read_text(str(asset_path))

                filtered_assets.append(filtered_asset)

        return filtered_assets

    @try_catch
    def build_prompt_variables(
        self,
        scene_index: int,
    ) -> Dict[str, Any]:
        scene_direction = self.get_scene_direction(scene_index)

        scene_transcript_string = self.get_scene_transcript(self.transcript, scene_index)

        variables = {
            "scene_index": scene_direction.get("scene", scene_index),
            "scene_startFrame": scene_direction.get("sceneStartFrame", 0),
            "scene_endFrame": scene_direction.get("sceneEndFrame", 0),
            "direction_video_description": scene_direction.get("videoDescription", ""),
            "audio_transcript_with_timings": scene_transcript_string,
        }

        self.logger.info(f"Built prompt variables for scene {scene_index}")

        return variables


    def run(self) -> list:
        """Override base run to return batched prompt paths."""
        self.manifest_controller.increment_gen_version(self.asset_type)
        self.delete_existing_outputs()
        self.delete_existing_prompts()
        self.logger.info(f"Deleted existing outputs for {self.asset_type}")
        if self.gen_prompt:
            self.save_prompt()
            self.logger.info(f"Saved prompts for {self.asset_type}")
        else:
            self.logger.info(f"Skipped saving prompts for {self.asset_type}")
        self.logger.info(f"Completed pre-processing for {self.asset_type}")
        self.gen_metadata_controller.save_metadata()

        return self._batch_prompt_paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-process video scene prompt")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--max_scenes', type=int, default=None, help='Maximum number of scenes to generate')
    parser.add_argument('--gen_prompt', type=lambda x: x.lower() == 'true', default=True, help='Generate prompts (default: true)')
    args = parser.parse_args()

    pre_process = VideoPreProcess(topic=args.topic, max_scenes=args.max_scenes, gen_prompt=args.gen_prompt)
    prompt_paths = pre_process.run()

    metadata = pre_process.metadata_controller.read(AssetType.VIDEO)

    pre_process.logger.info("=" * 80)
    pre_process.logger.info("Pre-processing completed successfully")
    pre_process.logger.info(f"Total scene videos to generate: {metadata['total_scenes']}")
    pre_process.logger.info(f"Prompt paths: {prompt_paths}")
    pre_process.logger.info("=" * 80)
