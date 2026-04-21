"""
CLI Pipeline — unified entry point for video generation steps.

Usage:
  python -m scripts.cli_pipeline init    --topic TOPIC --script PATH [--style STYLE] [--ratio RATIO] [--voice-id ID]
  python -m scripts.cli_pipeline pre     --topic TOPIC --step STEP
  python -m scripts.cli_pipeline post    --topic TOPIC --step STEP [--use-fallback]
  python -m scripts.cli_pipeline info    --topic TOPIC
  python -m scripts.cli_pipeline prompts --topic TOPIC --step STEP

Steps: direction, audio, assets, code
"""

import sys
import os
import json
import asyncio
import argparse
from pathlib import Path

from dotenv import load_dotenv

# Resolve all paths relative to this file so the pipeline works on any machine.
# Layout: <OVG_ROOT>/scripts/cli_pipeline.py
_OVG_ROOT = Path(__file__).resolve().parent.parent
_OUTPUTS_DIR = _OVG_ROOT / "Outputs"
_INVOCATION_CWD = Path.cwd()  # Capture the user's CWD so relative args can still be resolved.

if str(_OVG_ROOT) not in sys.path:
    sys.path.insert(0, str(_OVG_ROOT))

load_dotenv(_OVG_ROOT / ".env")

_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
os.environ["VIDEO_GEN_OUTPUTS_PATH"] = str(_OUTPUTS_DIR)

from scripts.enums import AssetType
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.logging_config import set_console_logging

STEP_TO_ASSET = {
    "direction": AssetType.DIRECTION,
    "audio": AssetType.AUDIO,
    "assets": AssetType.ASSETS,
    "code": AssetType.VIDEO,
}


def cmd_init(args):
    """Initialize a video project: create manifest, save script."""
    topic = args.topic
    manifest = ManifestController()
    manifest.set_topic(topic)
    io = SystemIOController()

    # Read script content
    script_path = args.script
    if not os.path.exists(script_path):
        print(f"ERROR: Script file not found: {script_path}")
        sys.exit(1)

    script_content = io.read_text(script_path)
    if not script_content:
        print(f"ERROR: Script file is empty: {script_path}")
        sys.exit(1)

    # Update metadata
    if args.style:
        manifest.update_metadata("video_style", args.style)
    if args.ratio:
        manifest.update_metadata("video_ratio", args.ratio)
    if args.voice_id:
        manifest.update_metadata("voice_id", args.voice_id)

    # Save script to the expected location
    config = ClaudeCliConfig(topic)
    script_dest = config.get_latest_path(AssetType.SCRIPT)
    Path(script_dest).parent.mkdir(parents=True, exist_ok=True)
    io.write_text(script_dest, script_content)

    # Set dimensions based on ratio
    manifest.set_dimensions()

    manifest_path = f"Outputs/{topic}/manifest.json"
    manifest_data = io.read_json(manifest_path)

    print(f"Initialized video project: {topic}")
    print(f"  Script saved to: {script_dest}")
    print(f"  Manifest: {manifest_path}")
    print(f"  Style: {manifest_data.get('metadata', {}).get('video_style', 'N/A')}")
    print(f"  Ratio: {manifest_data.get('metadata', {}).get('video_ratio', 'N/A')}")
    print(f"  Viewport: {manifest_data.get('metadata', {}).get('viewport_width', '?')}x{manifest_data.get('metadata', {}).get('viewport_height', '?')}")


def cmd_pre(args):
    """Run pre-processing for a step: build prompt from templates."""
    topic = args.topic
    step = args.step
    asset_type = STEP_TO_ASSET.get(step)
    if not asset_type:
        print(f"ERROR: Unknown step: {step}. Must be one of: {list(STEP_TO_ASSET.keys())}")
        sys.exit(1)

    from scripts.server_agents.claude_sdk_config import get_preprocessing_class

    pre_class = get_preprocessing_class(asset_type)
    if not pre_class:
        print(f"ERROR: No pre-processor for step: {step}")
        sys.exit(1)

    preprocessor = pre_class(topic=topic)
    result = preprocessor.run()

    if result is None and step == "assets":
        print("SKIP: No assets to generate (empty required_assets)")
        return

    if result:
        print(f"Pre-processing complete for {step}")
        print(f"  Prompt saved to: {result}")
    else:
        print(f"ERROR: Pre-processing failed for {step}")
        sys.exit(1)


def cmd_post(args):
    """Run post-processing for a step: validate, version, upload."""
    topic = args.topic
    step = args.step
    asset_type = STEP_TO_ASSET.get(step)
    if not asset_type:
        print(f"ERROR: Unknown step: {step}. Must be one of: {list(STEP_TO_ASSET.keys())}")
        sys.exit(1)

    from scripts.server_agents.claude_sdk_config import get_postprocessing_class

    post_class = get_postprocessing_class(asset_type)
    if not post_class:
        print(f"ERROR: No post-processor for step: {step}")
        sys.exit(1)

    kwargs = {"topic": topic}
    if step == "audio" and args.use_fallback:
        kwargs["use_fallback"] = True

    post_processor = post_class(**kwargs)
    success, file_path = asyncio.run(post_processor.run())

    if success and file_path:
        print(f"Post-processing complete for {step}")
        print(f"  Output: {file_path}")
    else:
        print(f"ERROR: Post-processing failed for {step}")
        sys.exit(1)


def cmd_info(args):
    """Show current manifest state for a video project."""
    topic = args.topic
    manifest_path = f"Outputs/{topic}/manifest.json"
    io = SystemIOController()

    if not os.path.exists(manifest_path):
        print(f"ERROR: No project found at {manifest_path}")
        sys.exit(1)

    data = io.read_json(manifest_path)
    print(json.dumps(data, indent=2))


def cmd_prompts(args):
    """Show the prompt file path(s) for a step."""
    topic = args.topic
    step = args.step
    asset_type = STEP_TO_ASSET.get(step)
    if not asset_type:
        print(f"ERROR: Unknown step: {step}")
        sys.exit(1)

    config = ClaudeCliConfig(topic)

    if step == "code":
        # Code step has multiple prompts (batched)
        prompts_dir = f"Outputs/{topic}/Video/Prompts"
        if os.path.exists(prompts_dir):
            files = sorted(Path(prompts_dir).glob("prompt_*.md"))
            if files:
                print(f"Code prompts ({len(files)} batches):")
                for f in files:
                    print(f"  {f}")
            else:
                print("No code prompts found. Run pre-processing first.")
        else:
            print("No code prompts directory. Run pre-processing first.")
    else:
        prompt_path = config.get_prompt_path(asset_type)
        if os.path.exists(prompt_path):
            print(f"Prompt: {prompt_path}")
        else:
            print(f"No prompt found at {prompt_path}. Run pre-processing first.")


def main():
    parser = argparse.ArgumentParser(
        description="Video Generation CLI Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", help="Pipeline command")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a video project")
    p_init.add_argument("--topic", required=True, help="Topic/video ID (e.g., my-video-v2)")
    p_init.add_argument("--script", required=True, help="Path to script markdown file")
    p_init.add_argument("--style", default="vox", help="Video style (default: vox)")
    p_init.add_argument("--ratio", default="9:16", help="Video ratio (default: 9:16)")
    p_init.add_argument("--voice-id", default=None, help="ElevenLabs voice ID override")

    # pre
    p_pre = subparsers.add_parser("pre", help="Run pre-processing for a step")
    p_pre.add_argument("--topic", required=True, help="Topic/video ID")
    p_pre.add_argument("--step", required=True, choices=["direction", "audio", "assets", "code"])

    # post
    p_post = subparsers.add_parser("post", help="Run post-processing for a step")
    p_post.add_argument("--topic", required=True, help="Topic/video ID")
    p_post.add_argument("--step", required=True, choices=["direction", "audio", "assets", "code"])
    p_post.add_argument("--use-fallback", action="store_true", help="Use fallback TTS model (audio only)")

    # info
    p_info = subparsers.add_parser("info", help="Show manifest state")
    p_info.add_argument("--topic", required=True, help="Topic/video ID")

    # prompts
    p_prompts = subparsers.add_parser("prompts", help="Show prompt file paths")
    p_prompts.add_argument("--topic", required=True, help="Topic/video ID")
    p_prompts.add_argument("--step", required=True, choices=["direction", "audio", "assets", "code"])

    args = parser.parse_args()
    set_console_logging(True)

    # User-supplied paths are relative to the invocation CWD. Resolve them
    # before we chdir to the OVG root for the controllers.
    if args.command == "init":
        args.script = str((_INVOCATION_CWD / args.script).resolve())

    # Anchor CWD to the OVG root so every "Outputs/{topic}/..." path the
    # controllers build lands inside <OVG_ROOT>/Outputs/.
    os.chdir(_OVG_ROOT)

    if args.command == "init":
        cmd_init(args)
    elif args.command == "pre":
        cmd_pre(args)
    elif args.command == "post":
        cmd_post(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "prompts":
        cmd_prompts(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
