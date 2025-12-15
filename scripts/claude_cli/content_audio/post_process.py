"""
Audio Content Post-Processing - Generates audio from video script using ElevenLabs.

Reads script from video_manifest.json, generates audio with word-level timestamps,
saves to versioned output, and updates the manifest.
"""

import os
import sys
from typing import Optional, Tuple
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.utility.elevenlabs_tts import generate_audio as elevenlabs_generate
from scripts.enums import AssetType
from scripts.utility.config import ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID, ELEVENLABS_SPEED, ELEVENLABS_STABILITY, ELEVENLABS_SIMILARITY, ELEVEN_LABS_DICTIONARY

class PostProcessAudio(BasePostProcess):
    def __init__(self, topic: str):
        super().__init__(
            asset_type=AssetType.AUDIO,
            logger_name='PostProcessAudio',
            log_file_name='post-process-audio',
            topic=topic,
        )

        # ElevenLabs configuration
        self.config = {
            "voice_id": ELEVENLABS_VOICE_ID,
            "model_id": ELEVENLABS_MODEL_ID,
            "speed": ELEVENLABS_SPEED,
            "stability": ELEVENLABS_STABILITY,
            "similarity": ELEVENLABS_SIMILARITY
        }
        self.phonetics_dict_id = ELEVEN_LABS_DICTIONARY

        self.logger.info("AudioContentPostProcess initialized")

    @try_catch
    def read_script_from_manifest(self) -> Optional[str]:
        """Read script markdown file from path specified in manifest."""
        content_data = self.manifest_controller.get_field(AssetType.SCRIPT)
        file_path = content_data.get('path') if content_data else None

        if not file_path:
            self.logger.error("No script path found in manifest")
            return None

        script_text = self.file_io.read_text(file_path)
        if not script_text:
            self.logger.error(f"Failed to read script from: {file_path}")
            return None

        self.logger.info(f"Read script from: {file_path} ({len(script_text)} characters)")
        return script_text.strip()

    @try_catch
    def get_next_version(self) -> str:
        """Get the next version number for audio output."""
        return self.output_controller.getLatestVersion(AssetType.AUDIO) + 1

    @try_catch
    def generate_audio(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            audio_path = Path(self.claude_cli_config.get_latest_path(AssetType.AUDIO))
            transcript_path = Path(self.claude_cli_config.get_latest_path(AssetType.TRANSCRIPT))
            self.logger.info(f"Audio generation starting: {audio_path}, {transcript_path}")
            elevenlabs_generate(
                text=text,
                audio_output_path=str(audio_path),
                transcript_output_path=str(transcript_path),
                config=self.config,
                phonetics_dict_id=self.phonetics_dict_id
            )

            if not audio_path.exists():
                self.logger.error(f"Audio file was not created: {audio_path}")
                return None, None

            if not transcript_path.exists():
                self.logger.error(f"Transcript file was not created: {transcript_path}")
                return None, None

            self.logger.info(f"Audio generated successfully: {audio_path}")
            self.logger.info(f"Transcript generated successfully: {transcript_path}")

            return str(audio_path), str(transcript_path)

        except Exception as e:
            self.logger.error(f"Failed to generate audio: {str(e)}")
            return None, None

    @try_catch
    def update_manifest(self, audio_path: str, transcript_path: str, version: str) -> bool:
        """Update the video manifest with audio asset information."""
        self.logger.info(f"Updating video manifest with audio v{version}")

        # Update audio asset fields
        updates = {
            'assets.audio.latest_version': version,
            'assets.audio.path': audio_path,
            'assets.audio.transcript_path': transcript_path,
            'assets.audio.status': 'generated'
        }

        for field_path, value in updates.items():
            success = self.manifest_controller.update_field(field_path, value)
            if not success:
                self.logger.error(f"Failed to update manifest field: {field_path}")
                return False

        # Update current stage if audio was the next step
        manifest = self.manifest_controller.read()
        if manifest.get('current_stage') == 'script':
            self.manifest_controller.update_field('current_stage', 'audio')

        self.logger.info(f"Successfully updated video manifest with audio v{version}")
        return True

    @try_catch
    def process(self) -> Tuple[bool, Optional[str]]:
        self.logger.info("Starting audio content post-processing")
        self.gen_metadata_controller.set_metadata({"config": self.config})
        # Step 1: Read script from manifest
        script_data = self.read_script_from_manifest()
        if not script_data:
            self.logger.error("Failed to read script data")
            return False, None

        # Step 2: Extract voiceover text from script
        text = script_data
        if not text:
            self.logger.error("Failed to extract voiceover text")
            return False, None

        self.logger.info(f"Audio generation starting")
        audio_path, transcript_path = self.generate_audio(text)
        self.logger.info(f"Audio generation completed")

        if not audio_path:
            self.logger.error("Failed to generate audio")
            return False, None

        self.write_versioned_output(AssetType.AUDIO)
        self.write_versioned_output(AssetType.TRANSCRIPT)
        return True, audio_path

def main():
    """Main entry point for audio post-processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate audio from video script")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--log', action='store_true', default=True, help='Enable console logging')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')
    args = parser.parse_args()

    processor = PostProcessAudio(topic=args.topic)

    success, audio_path = processor.run()

    if success and audio_path:
        processor.logger.info(f"[SUCCESS] Audio generated: {audio_path}")
        print(f"\nAudio generated successfully: {audio_path}")
    else:
        processor.logger.error("[FAILED] Audio generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
