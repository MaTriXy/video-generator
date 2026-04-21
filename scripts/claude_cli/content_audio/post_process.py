import os
import sys
import json
import asyncio
import subprocess
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
    ELEVEN_LABS_DICTIONARY,
    ADD_EMOTIONS,
)
from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.logging_config import set_console_logging
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.utility.elevenlabs_tts import generate_audio_batched as elevenlabs_generate
from scripts.enums import AssetType
from scripts.claude_cli.content_video_direction.scene_timestamp_calculator import match_narration_to_transcript

# video-tools/ is a sibling of scripts/ under the OVG root.
_VIDEO_TOOLS_DIR = Path(__file__).resolve().parents[3] / "video-tools"


class PostProcessAudio(BasePostProcess):
    def __init__(self, topic: str, use_fallback: bool = False):
        super().__init__(
            asset_type=AssetType.AUDIO,
            logger_name='PostProcessAudio',
            log_file_name='post-process-audio',
            topic=topic,
        )

        self.use_fallback = use_fallback
        metadata = self.manifest_controller.get_metadata() or {}
        voice_id = metadata.get('voice_id')
        if not voice_id:
            voice_id = ELEVENLABS_FALLBACK_VOICE_ID if use_fallback else ELEVENLABS_PRIMARY_VOICE_ID
        speed = ELEVENLABS_SPEED
        self.config = {
            "voice_id": voice_id,
            "speed": speed,
            "stability": ELEVENLABS_STABILITY,
            "similarity": ELEVENLABS_SIMILARITY
        }
        self.phonetics_dict_id = ELEVEN_LABS_DICTIONARY
        self.logger.info(f"AudioContentPostProcess initialized (use_fallback={use_fallback}, voice_id={voice_id})")

    def generate_sound_effects(self) -> bool:
        """Read direction JSON, generate sound effects for required_audio_effects, save URLs back."""
        direction_field = self.manifest_controller.get_field(AssetType.DIRECTION)
        direction_path = direction_field.get("path") if direction_field else None

        if not direction_path or not Path(direction_path).exists():
            self.logger.error(f"Direction file not found: {direction_path}")
            return False

        direction_data = self.file_io.read_json(direction_path)
        effects = direction_data.get("required_audio_effects", [])
        if not effects:
            self.logger.info("No required_audio_effects in direction, skipping")
            return True

        effects_dir = Path(direction_path).parent.parent.parent / "public" / "sound_effects"
        effects_dir.mkdir(parents=True, exist_ok=True)

        all_success = True
        for effect in effects:
            name = effect.get("name", "")
            text = effect.get("audio_sound_description", "")
            duration = effect.get("duration")
            if duration is not None and duration < 0.5:
                duration = 0.5

            if not text:
                self.logger.warning(f"Skipping '{name}': empty audio_sound_description")
                continue

            cmd = [
                sys.executable, "-m", "scripts.tools_cli", "generate_sound_effect",
                "--text", text,
                "--output-dir", str(effects_dir),
            ]
            if duration is not None:
                cmd += ["--duration", str(duration)]

            proc = subprocess.run(cmd, cwd=str(_VIDEO_TOOLS_DIR), capture_output=True, text=True)
            result = None
            if proc.stdout:
                try:
                    result = json.loads(proc.stdout.strip().splitlines()[-1])
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON from tools_cli for '{name}': {proc.stdout}")

            if result and result.get("success"):
                effect["path"] = result["path"]
                effect["filename"] = result["filename"]
                self.logger.info(f"Sound effect '{name}' -> {result['path']}")
            else:
                all_success = False
                err = (result or {}).get("message") or proc.stderr or "unknown error"
                self.logger.error(f"Failed to generate sound effect '{name}': {err}")

        self.file_io.write_json(direction_path, direction_data)

        generated = sum(1 for e in effects if "url" in e)
        self.logger.info(f"Generated {generated}/{len(effects)} sound effects, saved to {direction_path}")
        return all_success

    def _get_audio_paths(self) -> Tuple[Path, Path]:
        return (
            Path(self.claude_cli_config.get_latest_path(AssetType.AUDIO)),
            Path(self.claude_cli_config.get_latest_path(AssetType.TRANSCRIPT))
        )

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

    def _get_versioned_direction_path(self) -> Optional[str]:
        direction_manifest = self.manifest_controller.get_field(AssetType.DIRECTION)
        if direction_manifest and direction_manifest.get('path'):
            return direction_manifest['path']
        return None

    def _validate_direction_file_exists(self) -> bool:
        versioned_path = self._get_versioned_direction_path()
        if not versioned_path or not self.file_io.exists(versioned_path):
            self.logger.error(f"Versioned direction file not found: {versioned_path}")
            return False
        return True

    def _calculate_timestamps_for_direction(self) -> Tuple[bool, Optional[str]]:
        versioned_path = self._get_versioned_direction_path()

        if not self._validate_direction_file_exists():
            return False, "Versioned direction file not found"

        direction_data = self.file_io.read_json(versioned_path)

        if not direction_data or 'scenes' not in direction_data:
            error_msg = "Invalid direction data: missing 'scenes' array"
            self.logger.error(error_msg)
            return False, error_msg

        transcript = self.output_controller.read_output(AssetType.TRANSCRIPT)

        if not transcript:
            error_msg = "No transcript found - cannot calculate timestamps"
            self.logger.error(error_msg)
            return False, error_msg

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
                error_msg = f"Scene {scene_idx}: Failed to match narration to transcript. Words not mapping properly at transcript_index: {transcript_index}"
                self.logger.error(error_msg)
                return False, error_msg

            computed_timestamps.append((start_ms, end_ms))
            transcript_index = next_index
            self.logger.info(f"Scene {scene_idx}: {start_ms}ms - {end_ms}ms")

        for scene_idx, scene in enumerate(direction_data['scenes']):
            if computed_timestamps[scene_idx] is not None:
                start_ms, end_ms = computed_timestamps[scene_idx]
                scene['sceneStartTime'] = start_ms
                scene['sceneEndTime'] = end_ms

        self.file_io.write_json(versioned_path, direction_data)

        self.logger.info(f"✓ Calculated timestamps for {total_scenes} scenes")
        return True, None

    async def _call_elevenlabs_api(self, text: str, model: str) -> Tuple[bool, Optional[str], Optional[str], int, int, str, int]:
        audio_path, transcript_path = self._get_audio_paths()

        self.logger.info(f"Audio generation starting with {model}: {audio_path}, {transcript_path}")

        success, error_msg, affected_count, total_count, char_count = await elevenlabs_generate(
            text=text,
            audio_output_path=str(audio_path),
            transcript_output_path=str(transcript_path),
            config=self.config,
            phonetics_dict_id=self.phonetics_dict_id,
            model_override=model
        )

        if success:
            print(f"[OK] Audio generated successfully with {model} (char count: {char_count})")
            self.logger.info(f"Audio generated successfully with {model}: {audio_path} (char count: {char_count})")

        return success, str(audio_path) if success else None, str(transcript_path) if success else None, affected_count, total_count, error_msg, char_count

    @try_catch(return_on_error=(False, None, None, {}))
    async def generate_audio(self, text: str, use_fallback: bool = False) -> Tuple[bool, Optional[str], Optional[str], Dict[str, Any]]:
        model = ELEVENLABS_FALLBACK_MODEL if use_fallback else ELEVENLABS_PRIMARY_MODEL

        success, audio_path, transcript_path, affected_count, total_count, error_msg, char_count = await self._call_elevenlabs_api(
            text, model
        )

        if success:
            return True, audio_path, transcript_path, {"char_count": char_count}

        if use_fallback:
            print(f"[ERROR] {model} also failed - try again later.")
            self.logger.error(f"Fallback model also failed: {error_msg}")
        else:
            self.logger.warning(f"{model} failed: {error_msg}")

        return False, None, None, {
            "affected_count": affected_count,
            "total_count": total_count,
            "error_msg": error_msg,
            "char_count": char_count
        }

    def _handle_success(self, audio_path: str, model_used: Optional[str], char_count: int = 0) -> Tuple[bool, Optional[str]]:
        self.logger.info(f"Audio generation completed (TTS char count: {char_count})")
        self.gen_metadata_controller.set_metadata({"model_used": model_used, "tts_char_count": char_count})
        self._write_versioned_outputs()
        self._mirror_audio_to_public(audio_path)

        success, error_msg = self._calculate_timestamps_for_direction()
        if not success:
            self.logger.error(f"Failed to calculate timestamps for direction: {error_msg}")
            return False, error_msg

        return True, audio_path

    def _mirror_audio_to_public(self, audio_path: str) -> None:
        """Copy the TTS MP3 into Outputs/{TOPIC}/public/audio/ so Remotion Studio's
        staticFile('audio/latest.mp3') resolves."""
        import shutil
        src = Path(audio_path)
        if not src.exists():
            return
        # src is Outputs/{TOPIC}/Audio/latest.mp3 -> two levels up is Outputs/{TOPIC}/
        public_audio_dir = src.parent.parent / "public" / "audio"
        public_audio_dir.mkdir(parents=True, exist_ok=True)
        dest = public_audio_dir / "latest.mp3"
        shutil.copyfile(src, dest)
        self.logger.info(f"Mirrored audio to public/: {dest}")

    @try_catch(return_on_error=(False, "Audio post-processing failed due to an unexpected error"))
    async def process(self) -> Tuple[bool, Optional[str]]:
        self.logger.info("Starting audio content post-processing")

        if not self._validate_direction_file_exists():
            error_msg = "Direction file must exist before audio generation"
            print(f"Error: {error_msg}")
            return False, error_msg

        self.generate_sound_effects()

        # Check if audio should be reused from primary video (batch mode)
        metadata = self.manifest_controller.get_metadata() or {}
        if metadata.get("skipAudioApiCall"):
            self.logger.info("skipAudioApiCall=True -- skipping TTS, running timestamp matching only")
            audio_path, _ = self._get_audio_paths()
            if not audio_path.exists():
                return False, "skipAudioApiCall=True but audio file not found at expected path"
            return self._handle_success(str(audio_path), None)

        self.gen_metadata_controller.set_metadata({"config": self.config})

        use_emotion_tags = ADD_EMOTIONS and not self.use_fallback
        if not ADD_EMOTIONS:
            self.logger.info("ADD_EMOTIONS=false, using original script without emotion tags")

        if self.use_fallback:
            self.logger.info(f"Using fallback model {ELEVENLABS_FALLBACK_MODEL} with original script (no emotion tags)")
            script_data, script_path = self.read_script(use_emotion_tags=False)

            if not script_data:
                error_msg = "Failed to read script data"
                self.logger.error(error_msg)
                print(f"Error: {error_msg}")
                return False, error_msg

            success, audio_path, transcript_path, fallback_info = await self.generate_audio(script_data, use_fallback=True)

            if success:
                return self._handle_success(audio_path, ELEVENLABS_FALLBACK_MODEL, fallback_info.get('char_count', 0))

            error_msg = f"Audio generation failed with fallback model: {fallback_info.get('error_msg', 'Unknown error')}"
            print(f"Error: {error_msg}")
            return False, error_msg

        self.logger.info(f"Generating audio with {ELEVENLABS_PRIMARY_MODEL} (emotion_tags={use_emotion_tags})")
        script_data_v3, script_path = self.read_script(use_emotion_tags=use_emotion_tags)

        if not script_data_v3:
            error_msg = "Failed to read script data"
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            return False, error_msg

        success, audio_path, transcript_path, fallback_info = await self.generate_audio(script_data_v3, use_fallback=False)

        if success:
            return self._handle_success(audio_path, ELEVENLABS_PRIMARY_MODEL, fallback_info.get('char_count', 0))

        self.logger.warning(f"{ELEVENLABS_PRIMARY_MODEL} failed, automatically retrying with {ELEVENLABS_FALLBACK_MODEL}")
        print(f"[RETRY] {ELEVENLABS_PRIMARY_MODEL} failed, automatically retrying with {ELEVENLABS_FALLBACK_MODEL}...")

        script_data_v2, _ = self.read_script(use_emotion_tags=False)

        if not script_data_v2:
            error_msg = "Failed to read script for fallback"
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            return False, error_msg

        success, audio_path, transcript_path, fallback_info = await self.generate_audio(script_data_v2, use_fallback=True)

        if success:
            return self._handle_success(audio_path, ELEVENLABS_FALLBACK_MODEL, fallback_info.get('char_count', 0))

        error_msg = f"Audio generation failed with both {ELEVENLABS_PRIMARY_MODEL} and {ELEVENLABS_FALLBACK_MODEL}: {fallback_info.get('error_msg', 'Unknown error')}"
        print(f"Error: {error_msg}")
        self.logger.error(error_msg)
        return False, error_msg


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate audio from video script")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--use-fallback', action='store_true', help='Use fallback model with stripped emotion tags')
    args = parser.parse_args()

    processor = PostProcessAudio(
        topic=args.topic,
        use_fallback=args.use_fallback
    )

    success, audio_path = await processor.run()

    if success and audio_path:
        processor.logger.info(f"[SUCCESS] Audio generated: {audio_path}")
    else:
        processor.logger.error("[FAILED] Audio generation failed or needs user decision")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
