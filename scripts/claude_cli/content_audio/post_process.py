import os
import sys
import json
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.utility.config import (
    ELEVENLABS_PRIMARY_VOICE_ID,
    ELEVENLABS_FALLBACK_VOICE_ID,
    ELEVENLABS_PRIMARY_MODEL,
    ELEVENLABS_FALLBACK_MODEL,
    ELEVENLABS_SPEED,
    ELEVENLABS_STABILITY,
    ELEVENLABS_SIMILARITY,
    ELEVEN_LABS_DICTIONARY
)
from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.utility.elevenlabs_tts import generate_audio as elevenlabs_generate
from scripts.enums import AssetType
from scripts.claude_cli.content_video_direction.scene_timestamp_calculator import match_narration_to_transcript


class PostProcessAudio(BasePostProcess):
    def __init__(self, topic: str, use_fallback: bool = False):
        super().__init__(
            asset_type=AssetType.AUDIO,
            logger_name='PostProcessAudio',
            log_file_name='post-process-audio',
            topic=topic,
        )

        self.use_fallback = use_fallback
        self.config = {
            "voice_id": ELEVENLABS_PRIMARY_VOICE_ID if not use_fallback else ELEVENLABS_FALLBACK_VOICE_ID,
            "speed": ELEVENLABS_SPEED,
            "stability": ELEVENLABS_STABILITY,
            "similarity": ELEVENLABS_SIMILARITY
        }
        self.phonetics_dict_id = ELEVEN_LABS_DICTIONARY
        self.logger.info(f"AudioContentPostProcess initialized (use_fallback={use_fallback})")

    def _get_audio_paths(self) -> Tuple[Path, Path]:
        return (
            Path(self.claude_cli_config.get_latest_path(AssetType.AUDIO)),
            Path(self.claude_cli_config.get_latest_path(AssetType.TRANSCRIPT))
        )

    def _output_json_status(self, status: str, **kwargs) -> None:
        output = {"status": status, **kwargs}
        print(json.dumps(output, indent=2))

    def _write_versioned_outputs(self) -> None:
        self.write_versioned_output(AssetType.AUDIO)
        self.write_versioned_output(AssetType.TRANSCRIPT)

    @try_catch(return_on_error=(None, None))
    def read_script(self, use_emotion_tags: bool = True) -> Tuple[Optional[str], Optional[str]]:
        if use_emotion_tags:
            file_path = self.claude_cli_config.get_variant_path(AssetType.SCRIPT)
            self.logger.info(f"Using emotion-tagged script: {file_path}")
        else:
            file_path = self.claude_cli_config.get_final_path(AssetType.SCRIPT)
            self.logger.info(f"Using original script (no emotion tags): {file_path}")

        if not Path(file_path).exists():
            self.logger.error(f"Script file not found: {file_path}")
            return None, None

        script_text = self.file_io.read_text(file_path)
        if not script_text:
            self.logger.error(f"Failed to read script from: {file_path}")
            return None, None

        self.logger.info(f"Read script from: {file_path} ({len(script_text)} characters)")
        return script_text.strip(), file_path

    def _validate_direction_file_exists(self) -> bool:
        direction_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)
        if not self.file_io.exists(direction_file):
            self.logger.error(f"Direction file not found: {direction_file}")
            return False
        return True

    @try_catch
    def _calculate_timestamps_for_direction(self) -> bool:
        direction_file = self.claude_cli_config.get_latest_path(AssetType.DIRECTION)

        if not self._validate_direction_file_exists():
            return False

        direction_data = self.file_io.read_json(direction_file)

        if not direction_data or 'scenes' not in direction_data:
            self.logger.error("Invalid direction data: missing 'scenes' array")
            return False

        transcript = self.output_controller.read_output(AssetType.TRANSCRIPT)

        if not transcript:
            self.logger.error("No transcript found - cannot calculate timestamps")
            return False

        self.logger.info(f"Transcript loaded: {len(transcript)} words")

        transcript_index = 0
        total_scenes = len(direction_data['scenes'])
        computed_timestamps = []

        for scene_idx, scene in enumerate(direction_data['scenes']):
            narration = scene.get('audioTranscriptPortion', '')

            if not narration:
                self.logger.warning(f"Scene {scene_idx}: No audioTranscriptPortion found")
                computed_timestamps.append(None)
                continue

            start_ms, end_ms, next_index, _, _ = match_narration_to_transcript(
                narration, transcript, transcript_index
            )

            if start_ms is None or end_ms is None:
                self.logger.error(f"Scene {scene_idx}: Failed to match. Narration: '{narration[:50]}...' at transcript_index: {transcript_index}")
                return False

            computed_timestamps.append((start_ms, end_ms))
            transcript_index = next_index
            self.logger.info(f"Scene {scene_idx}: {start_ms}ms - {end_ms}ms")

        for scene_idx, scene in enumerate(direction_data['scenes']):
            if computed_timestamps[scene_idx] is not None:
                start_ms, end_ms = computed_timestamps[scene_idx]
                scene['sceneStartTime'] = start_ms
                scene['sceneEndTime'] = end_ms

        self.file_io.write_json(direction_file, direction_data)

        direction_manifest = self.manifest_controller.get_field(AssetType.DIRECTION)
        if direction_manifest and direction_manifest.get('path'):
            self.file_io.write_json(direction_manifest['path'], direction_data)

        self.logger.info(f"✓ Calculated timestamps for {total_scenes} scenes")
        return True


    def _call_elevenlabs_api(self, text: str, model: str, log_prefix: str) -> Tuple[bool, Optional[str], Optional[str], int, int, str]:
        audio_path, transcript_path = self._get_audio_paths()

        self.logger.info(f"Audio generation starting with {model}: {audio_path}, {transcript_path}")

        success, error_msg, affected_count, total_count = elevenlabs_generate(
            text=text,
            audio_output_path=str(audio_path),
            transcript_output_path=str(transcript_path),
            config=self.config,
            phonetics_dict_id=self.phonetics_dict_id,
            model_override=model
        )

        if success:
            print(f"\033[92m[OK] Audio generated successfully with {log_prefix}\033[0m")
            self.logger.info(f"Audio generated successfully with {model}: {audio_path}")

        return success, str(audio_path) if success else None, str(transcript_path) if success else None, affected_count, total_count, error_msg

    @try_catch(return_on_error=(False, None, None, {}))
    def generate_audio(self, text: str, use_fallback: bool = False) -> Tuple[bool, Optional[str], Optional[str], Dict[str, Any]]:
        model = ELEVENLABS_FALLBACK_MODEL if use_fallback else ELEVENLABS_PRIMARY_MODEL
        log_prefix = "ElevenLabs v2" if use_fallback else "ElevenLabs v3"

        success, audio_path, transcript_path, affected_count, total_count, error_msg = self._call_elevenlabs_api(
            text, model, log_prefix
        )

        if success:
            return True, audio_path, transcript_path, {}

        if use_fallback:
            print(f"\033[91m[ERROR] {log_prefix} also failed - try again later.\033[0m")
            self.logger.error(f"Fallback model also failed: {error_msg}")
        else:
            self.logger.warning(f"{log_prefix} failed: {error_msg}")

        return False, None, None, {
            "affected_count": affected_count,
            "total_count": total_count,
            "error_msg": error_msg
        }

    def _handle_success(self, audio_path: str, model_used: str) -> Tuple[bool, str]:
        self.logger.info("Audio generation completed")
        self._write_versioned_outputs()

        if not self._calculate_timestamps_for_direction():
            self.logger.error("Failed to calculate timestamps for direction")
            return False, None

        return True, audio_path

    @try_catch(return_on_error=(False, None))
    def process(self) -> Tuple[bool, Optional[str]]:
        self.logger.info("Starting audio content post-processing")

        if not self._validate_direction_file_exists():
            self._output_json_status("error", message="Direction file must exist before audio generation")
            return False, None

        self.gen_metadata_controller.set_metadata({"config": self.config})

        use_emotion_tags = not self.use_fallback
        model_name = ELEVENLABS_FALLBACK_MODEL if self.use_fallback else ELEVENLABS_PRIMARY_MODEL

        log_msg = "Using fallback model v2.5 with original script (no emotion tags)" if self.use_fallback else "Generating audio with v3 using emotion-tagged script"
        self.logger.info(log_msg)

        script_data, script_path = self.read_script(use_emotion_tags=use_emotion_tags)

        if not script_data:
            self.logger.error("Failed to read script data")
            self._output_json_status("error", message="Failed to read script")
            return False, None

        success, audio_path, transcript_path, fallback_info = self.generate_audio(script_data, use_fallback=self.use_fallback)

        if success:
            return self._handle_success(audio_path, model_name)

        if self.use_fallback:
            self._output_json_status("error", message="Fallback model v2.5 also failed")
        else:
            self._output_json_status(
                "needs_fallback",
                affected_count=fallback_info.get("affected_count", 0),
                total_count=fallback_info.get("total_count", 0),
                message="ElevenLabs v3 returned corrupted timestamp data. Retry with v2.5 (original script without emotion tags will be used)?"
            )

        return False, None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate audio from video script")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--use-fallback', action='store_true', help='Use fallback model (v2.5) with stripped emotion tags')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    processor = PostProcessAudio(
        topic=args.topic,
        use_fallback=args.use_fallback
    )

    success, audio_path = processor.run()

    if success and audio_path:
        processor.logger.info(f"[SUCCESS] Audio generated: {audio_path}")
    else:
        processor.logger.error("[FAILED] Audio generation failed or needs user decision")
        sys.exit(1)


if __name__ == "__main__":
    main()
