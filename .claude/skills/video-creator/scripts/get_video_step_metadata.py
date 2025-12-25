#!/usr/bin/env python3

import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from scripts.enums import AssetType
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', required=True)
    parser.add_argument('--asset-type', required=True)

    args = parser.parse_args()

    ClaudeCliConfig.set_topic(args.topic)
    metadata_controller = VideoStepMetadataController()

    asset_type = AssetType(args.asset_type)
    metadata = metadata_controller.read(asset_type)

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
