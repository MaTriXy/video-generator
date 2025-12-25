import os
import sys
import json
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.utility.config import (
    ELEVENLABS_VOICE_ID,
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
            "voice_id": ELEVENLABS_VOICE_ID,
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
    def read_script_from_manifest(self, use_emotion_tags: bool = True) -> Tuple[Optional[str], Optional[str]]:
        content_data = self.manifest_controller.get_field(AssetType.SCRIPT)
        file_path = content_data.get('path') if content_data else None

        if not file_path:
            self.logger.error("No script path found in manifest")
            return None, None

        if use_emotion_tags:
            variant_path = self.claude_cli_config.get_variant_path(AssetType.SCRIPT)

            if Path(variant_path).exists():
                file_path = variant_path
                self.logger.info(f"Using emotion-tagged script: {file_path}")
            else:
                self.logger.warning(f"Emotion-tagged script not found at {variant_path}, using original")

        script_text = self.file_io.read_text(file_path)
        if not script_text:
            self.logger.error(f"Failed to read script from: {file_path}")
            return None, None

        self.logger.info(f"Read script from: {file_path} ({len(script_text)} characters)")
        return script_text.strip(), file_path


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
        log_prefix = "ElevenLabs Turbo v2.5" if use_fallback else "ElevenLabs v3"

        success, audio_path, transcript_path, affected_count, total_count, error_msg = self._call_elevenlabs_api(
            text, model, log_prefix
        )

        if success:
            return True, audio_path, transcript_path, {}

        if use_fallback:
            print("\033[91m[ERROR] ElevenLabs v2.5 also failed - try again later.\033[0m")
            self.logger.error(f"Fallback model also failed: {error_msg}")
        else:
            self.logger.warning(f"v3 failed: {error_msg}")

        return False, None, None, {
            "affected_count": affected_count,
            "total_count": total_count,
            "error_msg": error_msg
        }

    def _handle_success(self, audio_path: str, model_used: str) -> Tuple[bool, str]:
        self.logger.info("Audio generation completed")
        self._write_versioned_outputs()
        return True, audio_path

    @try_catch(return_on_error=(False, None))
    def process(self) -> Tuple[bool, Optional[str]]:
        self.logger.info("Starting audio content post-processing")
        self.gen_metadata_controller.set_metadata({"config": self.config})

        use_emotion_tags = not self.use_fallback
        model_name = ELEVENLABS_FALLBACK_MODEL if self.use_fallback else ELEVENLABS_PRIMARY_MODEL

        log_msg = "Using fallback model v2.5 with original script (no emotion tags)" if self.use_fallback else "Generating audio with v3 using emotion-tagged script"
        self.logger.info(log_msg)

        script_data, script_path = self.read_script_from_manifest(use_emotion_tags=use_emotion_tags)

        if not script_data:
            self.logger.error("Failed to read script data")
            self._output_json_status("error", message="Failed to read script from manifest")
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
