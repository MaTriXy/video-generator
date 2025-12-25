import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
# File is at .claude/skills/video-designer/scripts/validate_design.py
# Need to go up 5 levels to reach project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pydantic import ValidationError
from design_schema import DesignSceneModel
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.enums import AssetType


def construct_file_path(topic: str, scene_index: int) -> str:
    # Sanitize inputs to prevent path traversal
    if '..' in topic or '/' in topic or '\\' in topic:
        raise ValueError("Invalid topic name. Topic cannot contain '..' or path separators.")

    # Set topic in config
    ClaudeCliConfig.set_topic(topic)

    # Get the latest file path template
    template_path = ClaudeCliConfig.get_latest_path(AssetType.DESIGN)

    # Replace scene_index placeholder (template has {scene_index} after topic formatting)
    file_path = template_path.format(scene_index=scene_index)

    return file_path


def validate_design_file(file_path: str) -> tuple[bool, Optional[DesignSceneModel], Optional[str]]:
    # Check if file exists
    if not os.path.exists(file_path):
        return False, None, f"File not found: {file_path}"

    if not os.path.isfile(file_path):
        return False, None, f"Path exists but is not a file: {file_path}"

    # Read JSON file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        error_msg = (
            f"JSON Syntax Error:\n"
            f"  Error: {e.msg}\n"
            f"  Location: Line {e.lineno}, Column {e.colno}\n"
            f"  Hint: The JSON structure is broken. Check for missing commas (,), "
            f"misplaced brackets ([]), or braces ({{}}) around this line."
        )
        return False, None, error_msg
    except Exception as e:
        return False, None, f"Error reading file: {str(e)}"

    # Validate using Pydantic model
    try:
        validated_model = DesignSceneModel.model_validate(data)
        return True, validated_model, None
    except ValidationError as e:
        error_msg = format_validation_errors(e, os.path.basename(file_path))
        return False, None, error_msg


def format_validation_errors(validation_error: ValidationError, filename: str) -> str:
    errors = validation_error.errors()
    error_count = len(errors)

    # Group errors by category
    type_errors = []
    value_errors = []
    missing_errors = []
    other_errors = []

    for error in errors:
        error_type = error.get('type', '')
        if 'missing' in error_type:
            missing_errors.append(error)
        elif error_type.startswith('int_') or error_type.startswith('float_') or error_type.startswith('string_') or 'type' in error_type:
            type_errors.append(error)
        elif 'value_error' in error_type or error_type.startswith('greater_') or error_type.startswith('less_'):
            value_errors.append(error)
        else:
            other_errors.append(error)

    # Build error message
    lines = [
        f"\n[FAIL] Found {error_count} validation error(s) in '{filename}':\n"
    ]

    # Print missing fields
    if missing_errors:
        lines.append("Missing Required Fields:")
        for i, error in enumerate(missing_errors, 1):
            field_path = format_error_location(error['loc'])
            lines.append(f"  {i}. Field '{field_path}' is required but missing")
        lines.append("")

    # Print type errors
    if type_errors:
        lines.append("Type Errors:")
        for i, error in enumerate(type_errors, 1):
            field_path = format_error_location(error['loc'])
            msg = error.get('msg', 'Invalid type')
            input_value = error.get('input')
            lines.append(f"  {i}. {field_path}: {msg}")
            if input_value is not None:
                lines.append(f"      Got: {repr(input_value)}")
        lines.append("")

    # Print value errors
    if value_errors:
        lines.append("Value Errors:")
        for i, error in enumerate(value_errors, 1):
            field_path = format_error_location(error['loc'])
            msg = error.get('msg', 'Invalid value')
            lines.append(f"  {i}. {field_path}: {msg}")
        lines.append("")

    # Print other errors
    if other_errors:
        lines.append("Other Validation Errors:")
        for i, error in enumerate(other_errors, 1):
            field_path = format_error_location(error['loc'])
            msg = error.get('msg', 'Validation failed')
            lines.append(f"  {i}. {field_path}: {msg}")
        lines.append("")

    lines.append("Fix all these errors and re-run this script.\n")

    return "\n".join(lines)


def format_error_location(loc: tuple) -> str:
    parts = []
    for item in loc:
        if isinstance(item, int):
            parts[-1] = f"{parts[-1]}[{item}]"
        else:
            parts.append(str(item))
    return ".".join(parts)


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
  python scripts/validation/validate_design.py --file-path Outputs/missle-infographic/Design/v1/Design_9.json
        """
    )

    parser.add_argument('--topic', help='Topic name')
    parser.add_argument('--scene-index', type=int, help='Scene index')
    parser.add_argument('--file-path', help='Direct path to design file (alternative to --topic and --scene-index)')

    args = parser.parse_args()

    # Determine file path
    if args.file_path:
        file_path = args.file_path
    elif args.topic and args.scene_index is not None:
        try:
            file_path = construct_file_path(args.topic, args.scene_index)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        print("\nError: Either --file-path OR (--topic and --scene-index) must be provided.", file=sys.stderr)
        sys.exit(1)

    # Validate file extension
    if not file_path.lower().endswith('.json'):
        print(f"Error: The provided file '{file_path}' is not a .json file.", file=sys.stderr)
        sys.exit(1)

    # Validate the file
    is_valid, validated_model, error_message = validate_design_file(file_path)

    if is_valid:
        print(f"\n[PASS] Validation successful for '{os.path.basename(file_path)}'")
        sys.exit(0)
    else:
        print(error_message, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
