"""
TSX Syntax Validation - Validates TSX files using TypeScript compiler to catch syntax errors like mismatched tags.
"""

import sys
import os
import argparse
import subprocess
import re
from typing import Dict, Any, List, Tuple

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.enums import AssetType
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.logging_config import get_utility_logger, set_console_logging


class TsxSyntaxValidator:
    """Validates TSX syntax using TypeScript compiler (tsc)."""

    def __init__(
        self,
        topic: str,
        scene_index: int,
        console_logging: bool = False
    ):
        set_console_logging(console_logging)
        self.topic = topic
        self.scene_index = scene_index

        # Set topic in config
        ClaudeCliConfig.set_topic(topic)

        # Get the file path
        latest_path_template = ClaudeCliConfig.get_latest_path(AssetType.VIDEO)
        self.file_path = latest_path_template.format(scene_index=scene_index)

        # TypeScript working directory (where tsconfig.json is located)
        self.tsc_cwd = os.path.join(project_root, "visualise_video")

        # Initialize logger
        self.logger = get_utility_logger("TsxSyntaxValidator", "tsx-syntax-validation.log")
        self.logger.info(f"Initialized TsxSyntaxValidator for topic: {topic}, scene: {scene_index}")
        self.logger.info(f"File path: {self.file_path}")

    def check_file_exists(self) -> bool:
        """Check if the TSX file exists."""
        full_path = os.path.join(project_root, self.file_path)

        if not os.path.exists(full_path):
            self.logger.error(f"File does not exist: {full_path}")
            return False

        if os.path.getsize(full_path) == 0:
            self.logger.error(f"File is empty: {full_path}")
            return False

        self.logger.info(f"File exists: {full_path}")
        return True

    def run_tsc(self) -> Dict[str, Any]:
        """Run TypeScript compiler on the TSX file and return results."""
        full_path = os.path.join(project_root, self.file_path)

        # TypeScript compiler command
        cmd = [
            "npx",
            "tsc",
            "--noEmit",
            "--jsx", "react-jsx",
            "--esModuleInterop",
            "--skipLibCheck",
            full_path
        ]

        self.logger.info(f"Running tsc: {' '.join(cmd)}")
        self.logger.info(f"Working directory: {self.tsc_cwd}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.tsc_cwd,
                capture_output=True,
                text=True,
                shell=True  # Required for Windows npx
            )

            # tsc returns exit code 0 if no errors, non-zero if errors
            if result.returncode == 0:
                return {
                    "success": True,
                    "errors": [],
                    "raw_output": result.stdout
                }

            # Parse errors from stderr or stdout
            error_output = result.stderr or result.stdout
            errors = self.parse_tsc_errors(error_output)

            return {
                "success": False,
                "errors": errors,
                "raw_output": error_output
            }

        except FileNotFoundError:
            return {
                "success": False,
                "errors": [],
                "raw_output": "TypeScript compiler not found. Make sure node_modules is installed in visualise_video."
            }
        except Exception as e:
            return {
                "success": False,
                "errors": [],
                "raw_output": str(e)
            }

    # Error codes to ignore (import/module resolution related)
    IGNORED_ERROR_CODES = {
        "TS2307",  # Cannot find module 'X' or its corresponding type declarations
        "TS2306",  # File 'X' is not a module
        "TS2792",  # Cannot find module 'X'. Did you mean to set the 'moduleResolution' option?
        "TS2305",  # Module 'X' has no exported member 'Y'
        "TS2614",  # Module 'X' has no exported member 'Y'. Did you mean to use 'import X from ...'?
    }

    def parse_tsc_errors(self, output: str) -> List[Dict[str, Any]]:
        """Parse TypeScript compiler error output, filtering out import-related errors."""
        errors = []

        # Pattern: file(line,column): error TSxxxx: message
        pattern = r'([^(]+)\((\d+),(\d+)\):\s*(error|warning)\s+(TS\d+):\s*(.+)'

        for match in re.finditer(pattern, output):
            error_code = match.group(5)

            # Skip import/module resolution errors
            if error_code in self.IGNORED_ERROR_CODES:
                self.logger.info(f"Ignoring {error_code}: {match.group(6).strip()}")
                continue

            errors.append({
                "file": match.group(1).strip(),
                "line": int(match.group(2)),
                "column": int(match.group(3)),
                "severity": match.group(4).upper(),
                "code": error_code,
                "message": match.group(6).strip()
            })

        return errors

    def format_errors(self, errors: List[Dict[str, Any]]) -> str:
        """Format TypeScript errors for display."""
        if not errors:
            return "No errors found."

        output_lines = []

        for error in errors:
            output_lines.append(
                f"  [{error['severity']}] Line {error['line']}:{error['column']} - {error['message']}"
            )
            output_lines.append(f"           Code: {error['code']}")

        return "\n".join(output_lines)

    def validate(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Run full validation and return (is_valid, errors)."""
        self.logger.info("=" * 60)
        self.logger.info(f"Starting TSX syntax validation")
        self.logger.info(f"Topic: {self.topic}")
        self.logger.info(f"Scene: {self.scene_index}")
        self.logger.info(f"File: {self.file_path}")
        self.logger.info("=" * 60)

        # Check file exists
        if not self.check_file_exists():
            self.logger.info(f"[ERROR] File not found: {self.file_path}")
            return False, []

        # Run TypeScript compiler
        result = self.run_tsc()

        if result["success"]:
            self.logger.info("TSX syntax validation passed!")
            return True, []

        # Format and display errors (filtered - import errors are excluded)
        errors = result["errors"]

        # If no errors after filtering, consider it a success
        if not errors:
            self.logger.info("TSX syntax validation passed! (import-related errors were ignored)")
            print("[PASSED] TSX syntax validation passed")
            return True, []

        error_output = self.format_errors(errors)
        self.logger.info(f"Fix the following errors and run the validation again:\n{error_output}")
        print(f"[FAILED] TSX syntax validation errors:\n{error_output}")
        print(f"\nSummary: {len(errors)} error(s)")

        return False, errors


def main():
    parser = argparse.ArgumentParser(description="Validate TSX syntax using TypeScript compiler")
    parser.add_argument('--topic', type=str, required=True, help='Topic name for video generation')
    parser.add_argument('--scene_index', type=int, required=True, help='Scene index (0-based)')
    parser.add_argument('--log', action='store_true', default=False, help='Enable console logging')

    args = parser.parse_args()

    validator = TsxSyntaxValidator(
        topic=args.topic,
        scene_index=args.scene_index,
        console_logging=args.log
    )

    is_valid, errors = validator.validate()
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
