import os
import sys
import json
from typing import Optional, Tuple
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_post_process import BasePostProcess
from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.enums import AssetType

from scripts.claude_cli.claude_cli_config import ClaudeCliConfig

class PostProcessCreateVideoUserInput(BasePostProcess):
    def __init__(self, topic: str, video_style: str):
        super().__init__(
            asset_type=AssetType.SCRIPT,
            logger_name='PostProcessCreateVideoUserInput',
            log_file_name='post-process-create-video-user-input',
            topic=topic,
        )
        self.video_style_label = video_style
        self.video_style = None
        self.script_file = Path(f"Outputs/{topic}/Scripts/script-v1.md")
        self.script = None

    def validate_style(self) -> Optional[dict]:
        if self.video_style_label not in ClaudeCliConfig.STYLE_MAPPING:
            available = ", ".join(ClaudeCliConfig.STYLE_MAPPING.keys())
            return {
                "valid": False,
                "error": f"Invalid video style '{self.video_style_label}'. Available options: {available}",
            }
        self.video_style = ClaudeCliConfig.STYLE_MAPPING[self.video_style_label]
        return None

    def validate_script(self, limit: int = 2000) -> Optional[dict]:
        if not self.script or not self.script.strip():
            return {"valid": False, "error": "Script cannot be empty"}

        char_count = len(self.script.strip())
        if char_count >= limit:
            excess = char_count - limit
            return {
                "valid": False,
                "error": f"Script exceeds character limit by {excess} characters ({char_count}/{limit})",
            }
        return None

    @try_catch
    def process(self) -> Tuple[bool, Optional[dict]]:
        errors = []

        style_error = self.validate_style()
        if style_error:
            errors.append(style_error["error"])

        try:
            self.script = self.script_file.read_text(encoding='utf-8')
        except Exception as e:
            errors.append("Failed to read script file")
        else:
            script_error = self.validate_script()
            if script_error:
                errors.append(script_error["error"])

        if errors:
            return False, {"valid": False, "error": " | ".join(errors)}

        self.manifest_controller.update_file(AssetType.SCRIPT, str(self.script_file.as_posix()), 1)
        self.manifest_controller.update_metadata('video_style', self.video_style)

        return True, {"valid": True, "video_style": self.video_style}

    def run(self) -> Tuple[bool, Optional[dict]]:
        return self.process()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Process user input for video creation")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--video-style', type=str, required=True, help='Video style ID')
    args = parser.parse_args()

    processor = PostProcessCreateVideoUserInput(topic=args.topic, video_style=args.video_style)
    success, result = processor.run()
    print(json.dumps(result, indent=2))

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
