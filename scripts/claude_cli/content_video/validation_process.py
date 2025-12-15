import sys
import os
import argparse
from pathlib import Path
from typing import Tuple

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.base_validate_process import BaseValidateProcess
from scripts.logging_config import set_console_logging


class SceneValidateProcess(BaseValidateProcess):
    def __init__(
        self,
        lesson_index: int,
        material_index: int,
        scene_index: int,
        console_logging: bool = False
    ):
        file_name = f"latest_lesson_{lesson_index}_material_{material_index}_scene_{scene_index}_video_output.tsx"
        file_path = str(Path("Outputs/Video/Claude-cli") / file_name)

        super().__init__(
            course_metadata={
                "lesson_index": lesson_index,
                "material_index": material_index,
                "scene_index": scene_index
            },
            file_path=file_path,
            generation_type="content-scene",
            logger_name="SceneFileVerification",
            log_file_name="scene-file-verification.log",
            console_logging=console_logging,
            schema=None  # TSX files don't need schema validation
        )

        self.lesson_index = lesson_index
        self.material_index = material_index
        self.scene_index = scene_index


def main():
    parser = argparse.ArgumentParser(description="Verify scene file existence")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--lesson', type=int, required=True, help='Lesson index (0-based)')
    parser.add_argument('--material', type=int, required=True, help='Material index (0-based)')
    parser.add_argument('--scene', type=int, required=True, help='Scene index (0-based)')
    parser.add_argument('--log', action='store_true', default=False, help='Enable console logging (default: False)')
    parser.add_argument('--no-log', action='store_false', dest='log', help='Disable console logging')

    args = parser.parse_args()

    # Create validator instance
    validator = SceneValidateProcess(
        lesson_index=args.lesson,
        material_index=args.material,
        scene_index=args.scene,
        console_logging=args.log
    )

    validator.validate()


if __name__ == "__main__":
    main()
