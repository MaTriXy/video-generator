#!/usr/bin/env python3

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from scripts.controllers.video_step_sub_status_controller import VideoStepSubStatusController
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.enums import AssetType


MULTI_AGENT_STEPS = [AssetType.DESIGN, AssetType.VIDEO]


class VideoStepSubStatus:
    def __init__(self, topic: str):
        self.topic = topic
        self.controller = VideoStepSubStatusController()
        self.controller.set_topic(topic)
        self.io_controller = SystemIOController()
        ClaudeCliConfig.set_topic(topic)

    def get_next_step(self, asset_type: AssetType):
        result = self.controller.get_next_step(asset_type)
        action = result['action']
        subagents = result.get('subagents', [])
        is_multi_agent = asset_type in MULTI_AGENT_STEPS

        if action == 'run_preprocessing':
            print("START FROM PRE_PROCESSING_STEP")
        elif action == 'run_subagents':
            if is_multi_agent:
                print(f"Skip preprocessing and start by running onlyx {len(subagents)} subagents.")
            else:
                print("Skip preprocessing and start by running subagent")
        elif action == 'run_post_processing':
            print("Skip preprocessing and running subagents, only run the post processing script")

    def mark_complete(self, asset_type: AssetType, subagent_id: int):
        success = self.controller.mark_subagent_completed(asset_type, subagent_id)

        if success:
            print(f"[SUCCESS] Marked subagent {subagent_id} as completed for {asset_type.value}")
        else:
            print(f"[INFO] Subagent {subagent_id} was already marked as completed for {asset_type.value}")

    def init_subagent(self, asset_type: AssetType):
        result = self.controller.claim_next_subagent(asset_type)

        if not result['success']:
            print("No scenes available to process. Stop immediately")
            return

        scene_index = result['scene_index']

        latest_path_template = ClaudeCliConfig.get_latest_path(asset_type)
        output_path = latest_path_template.format(scene_index=scene_index)

        if self.io_controller.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"You will be working on scene {scene_index}. Skip all the steps below and only run the validation step")
        else:
            print(f"You will be working on scene {scene_index}. You will be implementing all the below steps")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--command', required=True)
    parser.add_argument('--topic', required=True)
    parser.add_argument('--asset-type', required=True)
    parser.add_argument('--subagent-id', type=int)

    args = parser.parse_args()

    manager = VideoStepSubStatus(args.topic)
    asset_type = AssetType(args.asset_type)

    if args.command == 'get-next-step':
        manager.get_next_step(asset_type)
    elif args.command == 'mark-complete':
        manager.mark_complete(asset_type, args.subagent_id)
    elif args.command == 'init-subagent':
        manager.init_subagent(asset_type)

    sys.exit(0)


if __name__ == "__main__":
    main()
