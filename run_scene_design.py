"""
Scene Design Generator using Claude Code SDK

This script:
1. Runs pre-processing for video design
2. Uses Claude Code SDK to invoke the content_scene_design_generator agent
3. Generates design specifications for a specific scene using the video-designer skill
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from claude_code_sdk import query, ClaudeCodeOptions, Message
from scripts.claude_cli.content_video_design.pre_process import VideoDesignPreProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.enums import AssetType
from scripts.logging_config import get_utility_logger, set_console_logging


class SceneDesignRunner:
    """Runs scene design generation using Claude Code SDK."""

    def __init__(self, topic: str, scene_index: int, console_logging: bool = True):
        self.topic = topic
        self.scene_index = scene_index
        self.console_logging = console_logging
        self.project_root = project_root

        # Setup logging
        set_console_logging(console_logging)
        ClaudeCliConfig.set_topic(topic)
        log_dir = Path(ClaudeCliConfig.BASE_OUTPUT_PATH) / topic / "logs"
        self.logger = get_utility_logger(
            'SceneDesignRunner',
            'scene-design-runner',
            log_dir
        )

    def run_pre_processing(self) -> int:
        """Run pre-processing to generate prompts for all scenes."""
        self.logger.info(f"Running pre-processing for topic: {self.topic}")

        pre_process = VideoDesignPreProcess(topic=self.topic)
        pre_process.run()

        # Read metadata to get total scene count
        metadata_path = pre_process.design_meta_data_path
        metadata = pre_process.file_io.read_json(metadata_path)
        total_scenes = metadata.get('total_scenes', 0)

        self.logger.info(f"Pre-processing completed. Total scenes: {total_scenes}")

        if self.scene_index >= total_scenes:
            raise ValueError(
                f"Scene index {self.scene_index} is out of range. "
                f"Total scenes available: {total_scenes}"
            )

        return total_scenes

    def _get_agent_prompt(self) -> str:
        """Build the prompt for the content_scene_design_generator agent."""
        return f"--topic \"{self.topic}\" --scene {self.scene_index}"

    async def run_agent(self) -> str:
        """Run the content_scene_design_generator agent using Claude Code SDK."""
        self.logger.info(f"Starting agent for scene {self.scene_index}")

        agent_prompt = self._get_agent_prompt()

        options = ClaudeCodeOptions(
            cwd=str(self.project_root),
            allowed_tools=[
                "Read", "Write", "Bash", "Glob", "Grep",
                "Skill", "Task"
            ],
            permission_mode="acceptEdits",
            model="sonnet",
            agent_name="content_scene_design_generator",
        )

        result_text = []

        self.logger.info(f"Invoking agent with prompt: {agent_prompt}")

        async for message in query(
            prompt=agent_prompt,
            options=options
        ):
            if isinstance(message, Message):
                for block in message.content:
                    if hasattr(block, 'text'):
                        result_text.append(block.text)
                        if self.console_logging:
                            print(block.text)

        final_result = "\n".join(result_text)
        self.logger.info(f"Agent completed for scene {self.scene_index}")

        return final_result

    async def run(self) -> str:
        """Execute the complete workflow: pre-processing + agent execution."""
        self.logger.info("=" * 80)
        self.logger.info(f"Starting scene design generation")
        self.logger.info(f"Topic: {self.topic}")
        self.logger.info(f"Scene Index: {self.scene_index}")
        self.logger.info("=" * 80)

        # Step 1: Run pre-processing
        total_scenes = self.run_pre_processing()

        # Step 2: Run the agent
        result = await self.run_agent()

        # Log completion
        output_path = ClaudeCliConfig.get_latest_path(AssetType.DESIGN).format(
            scene_index=self.scene_index
        )

        self.logger.info("=" * 80)
        self.logger.info("Scene design generation completed successfully")
        self.logger.info(f"Output saved to: {output_path}")
        self.logger.info("=" * 80)

        return result


async def main():
    parser = argparse.ArgumentParser(
        description="Generate video design specification for a specific scene using Claude Code SDK"
    )
    parser.add_argument(
        '--topic',
        type=str,
        required=True,
        help='Topic name for video generation'
    )
    parser.add_argument(
        '--scene',
        type=int,
        required=True,
        help='Scene index (0-based) to generate design for'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=True,
        help='Enable verbose console output'
    )
    parser.add_argument(
        '--skip-preprocess',
        action='store_true',
        default=False,
        help='Skip pre-processing (use if prompts are already generated)'
    )

    args = parser.parse_args()

    runner = SceneDesignRunner(
        topic=args.topic,
        scene_index=args.scene,
        console_logging=args.verbose
    )

    if args.skip_preprocess:
        # Only run the agent
        result = await runner.run_agent()
    else:
        # Full workflow
        result = await runner.run()

    print("\n" + "=" * 80)
    print("COMPLETED")
    print("=" * 80)

    return result


if __name__ == "__main__":
    asyncio.run(main())
