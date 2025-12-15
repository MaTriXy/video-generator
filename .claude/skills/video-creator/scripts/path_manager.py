#!/usr/bin/env python3

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from scripts.enums import AssetType
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.manifest_controller import ManifestController


class PathManager:

    def __init__(self, topic: str):
        self.topic = topic
        ClaudeCliConfig.set_topic(topic)
        self.manifest_controller = ManifestController()
        self.manifest_controller.set_topic(topic)

    def get_path(self, asset_type: str, scene_index: Optional[int] = None, subpath: Optional[str] = None) -> str:

        asset = AssetType(asset_type)

        if subpath == 'latest':
            path = ClaudeCliConfig.get_latest_path(asset)
            if scene_index is not None:
                path = path.replace('{scene_index}', str(scene_index))
            return path
        elif subpath == 'prompt':
            path = ClaudeCliConfig.get_prompt_path(asset)
            if scene_index is not None:
                path = path.replace('{scene_index}', str(scene_index))
            return path
        elif subpath == 'metadata':
            return ClaudeCliConfig.get_metadata_path(asset)
        elif subpath == 'manifest':
            return self.manifest_controller.manifest_path
        elif subpath == 'full-video-tasks':
            return f"Outputs/{self.topic}/full-video-tasks.json"
        elif subpath == 'script-file':
            return ClaudeCliConfig.get_final_path(asset)
        else:
            return f"Outputs/{self.topic}/{asset.value}"

    def list_directory_files(self, asset_type: str, scene_index: Optional[int] = None, pattern: Optional[str] = None) -> List[str]:

        try:
            dir_path = Path(self.get_path(asset_type, scene_index))

            if dir_path.is_file():
                dir_path = dir_path.parent

            if not dir_path.exists() or not dir_path.is_dir():
                return []

            if pattern:
                files = list(dir_path.glob(pattern))
            else:
                files = [f for f in dir_path.iterdir() if f.is_file()]

            return [str(f.absolute()) for f in sorted(files)]

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return []

    def print_path_info(self, paths: List[str], message: str, quiet: bool = False):

        if not quiet:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"  {message}", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

            if not paths:
                print("  No paths found.", file=sys.stderr)
            else:
                for path in paths:
                    print(f"  - {path}", file=sys.stderr)

            print(f"{'='*60}\n", file=sys.stderr)

        for path in paths:
            print(path)


def main():

    parser = argparse.ArgumentParser(description="Centralized path management for Claude CLI")

    parser.add_argument("--topic", type=str, required=True)
    parser.add_argument("--asset-type", type=str, required=True)
    parser.add_argument("--scene-index", type=int)
    parser.add_argument("--subpath", type=str, default='latest')
    parser.add_argument("--list-files", action="store_true")
    parser.add_argument("--pattern", type=str)
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    try:
        manager = PathManager(topic=args.topic)

        if args.list_files:
            paths = manager.list_directory_files(args.asset_type, args.scene_index, args.pattern)

            message = f"Files in {args.asset_type} for topic '{args.topic}'"
            if args.scene_index is not None:
                message += f" (scene {args.scene_index})"
            if args.pattern:
                message += f" matching '{args.pattern}'"

            manager.print_path_info(paths, message, args.quiet)
        else:
            path = manager.get_path(args.asset_type, args.scene_index, args.subpath)

            message = f"Path for {args.asset_type} (topic: {args.topic})"
            if args.scene_index is not None:
                message += f" [scene {args.scene_index}]"
            if args.subpath:
                message += f" [{args.subpath}]"

            manager.print_path_info([path], message, args.quiet)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
