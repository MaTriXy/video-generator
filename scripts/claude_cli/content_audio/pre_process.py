"""
Audio Pre-Process - Prepares prompt with output path for audio emotion tagging.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.base_pre_process import BasePreProcess
from scripts.controllers.utils.decorators.try_catch import try_catch


class AudioPreProcess(BasePreProcess):

    def __init__(self, topic: str):
        super().__init__(
            asset_type=AssetType.AUDIO,
            logger_name='AudioPreProcess',
            log_file_name="audio-pre-process",
            topic=topic,
            gen_prompt=True,
        )

    @try_catch
    def build_prompt_variables(self) -> Dict[str, Any]:
        return {}

    @try_catch
    def save_prompt(self) -> None:
        script_path = self.claude_cli_config.get_final_path(AssetType.SCRIPT)
        script_content = self.file_io.read_text(script_path)

        prompt = f"""<video_id>{self.video_id}</video_id>

<script>
{script_content}
</script>"""

        self.save_prompt_to_file(prompt)
        self.logger.info(f"Saved audio prompt to: {self.prompt_path}")

    def run(self) -> str:
        return super().run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pre-process audio prompt")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for audio generation')
    args = parser.parse_args()

    pre_process = AudioPreProcess(topic=args.topic)
    pre_process.run()
