"""
Save Agent Output Tool

Writes content to the appropriate latest file path based on asset type.
Uses ClaudeCliConfig to determine the correct output path.
"""

import os
import json
import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.enums import AssetType
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig


def write_asset(asset_type: AssetType, content: str, scene_index: int | None = None) -> str:
    latest_path = ClaudeCliConfig.get_latest_path(asset_type)

    if "{scene_index}" in latest_path:
        if scene_index is None:
            raise ValueError(f"scene_index is required for {asset_type.value} asset type")
        latest_path = latest_path.format(scene_index=scene_index)

    # Ensure directory exists
    output_path = Path(latest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content based on file extension
    if latest_path.endswith('.json'):
        # Try to parse as JSON first, if it fails write as raw string in a wrapper
        try:
            parsed = json.loads(content)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # Write raw content if not valid JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
    else:
        # Write as plain text for non-JSON files (.tsx, .mp3, etc.)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return str(output_path)


def get_asset_type_from_string(type_string: str) -> AssetType:
    """Convert a string to an AssetType enum value."""
    type_map = {
        "research": AssetType.RESEARCH,
        "script": AssetType.SCRIPT,
        "scripts": AssetType.SCRIPT,
        "transcript": AssetType.TRANSCRIPT,
        "audio": AssetType.AUDIO,
        "direction": AssetType.DIRECTION,
        "design": AssetType.DESIGN,
        "video": AssetType.VIDEO,
    }

    normalized = type_string.lower().strip()
    if normalized not in type_map:
        valid_types = list(type_map.keys())
        raise ValueError(f"Invalid asset type '{type_string}'. Valid types: {valid_types}")

    return type_map[normalized]


def main():
    parser = argparse.ArgumentParser(
        description="Write content to the appropriate asset output path"
    )
    parser.add_argument(
        "--save_type",
        type=str,
        help="type (research, script, transcript, audio, direction, design, video)"
    )
    parser.add_argument(
        "--content",
        type=str,
        help="Content string to write"
    )
    parser.add_argument(
        "--scene_index",
        type=int,
        default=None,
        help="Scene index (required for design and video asset types)"
    )
    args = parser.parse_args()

    try:
        asset_type = get_asset_type_from_string(args.save_type)
        output_path = write_asset(asset_type, args.content, args.scene_index)
        print(f"Content written to: {output_path}")

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
