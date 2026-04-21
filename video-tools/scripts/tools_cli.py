"""Bash-callable dispatcher for all video-tools utilities.

Usage (from C:/Outscal/OVG/video-tools):
  python -m scripts.tools_cli get_asset            --payload payload.json
  python -m scripts.tools_cli describe_images      --urls url1,url2,...
  python -m scripts.tools_cli svg_path             --equation PARABOLIC --params-json '{"start_x":0,...}'
  python -m scripts.tools_cli merge_paths          --paths-json '["d1","d2"]'
  python -m scripts.tools_cli validate_json        --file path.json [--topic TOPIC --step STEP]
  python -m scripts.tools_cli validate_tsx         --payload payload.json
  python -m scripts.tools_cli validate_script_with_emotions --file path.md --topic TOPIC
  python -m scripts.tools_cli generate_sound_effect --text "..." [--duration 3] [--prompt-influence 0.3]

Result is always printed to STDOUT as JSON. Logs are written to logs/ only (stderr on error).
Pass --verbose to stream INFO logs to the console.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Resolve paths relative to this file so tools work on any machine.
# Layout: <OVG_ROOT>/video-tools/scripts/tools_cli.py
ROOT_DIR = Path(__file__).resolve().parent.parent
_OVG_ROOT = ROOT_DIR.parent
_OUTPUTS_DIR = _OVG_ROOT / "Outputs"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(_OVG_ROOT / ".env")
os.environ["VIDEO_GEN_OUTPUTS_PATH"] = str(_OUTPUTS_DIR)

from scripts.logging_config import set_console_logging


def _emit(result) -> int:
    """Print result as JSON on stdout. Return 0 on success, 1 on failure."""
    print(json.dumps(result, default=str))
    if isinstance(result, dict) and result.get("success") is False:
        return 1
    return 0


def _load_payload(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_get_asset(args) -> int:
    from scripts.assets.get_asset_tool import get_asset_batch
    payload = _load_payload(args.payload)
    assets = payload.get("assets", [])
    art_style = payload.get("art_style", "")
    output_path = payload.get("output_path", "")
    results = asyncio.run(get_asset_batch(assets, art_style=art_style, output_path=output_path))
    return _emit(results)


def cmd_describe_images(args) -> int:
    from scripts.assets.describe_images_tool import describe_images
    if args.urls_file:
        urls = _load_payload(args.urls_file)
        if isinstance(urls, dict):
            urls = urls.get("urls", [])
    else:
        urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    results = asyncio.run(describe_images(urls))
    return _emit(results)


def cmd_svg_path(args) -> int:
    from scripts.svg_gen.svg_path_tool import get_path
    params = json.loads(args.params_json) if args.params_json else {}
    path = get_path(args.equation, **params)
    return _emit({"success": True, "path": path})


def cmd_merge_paths(args) -> int:
    from scripts.svg_gen.merge_paths_tool import merge_paths
    if args.paths_file:
        paths = _load_payload(args.paths_file)
        if isinstance(paths, dict):
            paths = paths.get("paths", [])
    else:
        paths = json.loads(args.paths_json)
    merged = merge_paths(paths)
    return _emit({"success": True, "path": merged})


def cmd_validate_json(args) -> int:
    from scripts.validation.validate_json_tool import validate_json
    content = Path(args.file).read_text(encoding="utf-8")
    result = validate_json(content)

    # Optional: mirror the old MCP behaviour of writing the validated JSON into
    # the direction Latest folder when --topic is supplied.
    if result.get("success") and args.topic:
        outputs_path = os.environ.get("VIDEO_GEN_OUTPUTS_PATH")
        if outputs_path:
            dest = Path(outputs_path) / args.topic / "Direction" / "Latest" / "latest.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            result["written_to"] = str(dest)
    return _emit(result)


def cmd_validate_tsx(args) -> int:
    from scripts.validation.validate_tsx_tool import validate_tsx_batch
    payload = _load_payload(args.payload)
    components = payload.get("components", [])
    total_frames = payload.get("total_frames", 600)

    # Auto-fill output_path for each component if topic supplied and not set
    topic = payload.get("topic") or args.topic
    outputs_path = os.environ.get("VIDEO_GEN_OUTPUTS_PATH")
    if topic and outputs_path:
        for comp in components:
            if "scene_index" in comp and not comp.get("output_path"):
                comp["output_path"] = str(
                    Path(outputs_path) / topic / "Video" / "Latest" / f"scene_{comp['scene_index']}.tsx"
                )

    results = asyncio.run(validate_tsx_batch(components, total_frames=total_frames))
    return _emit(results)


def cmd_validate_script_with_emotions(args) -> int:
    from scripts.validation.validate_script_with_emotions_tool import validate_script_with_emotions
    tagged_script = Path(args.file).read_text(encoding="utf-8")
    result = validate_script_with_emotions(tagged_script, args.topic)
    return _emit(result)


def cmd_generate_sound_effect(args) -> int:
    from scripts.sound_effect.generate_sound_effect_tool import generate_sound_effect
    result = asyncio.run(generate_sound_effect(
        text=args.text,
        duration_seconds=args.duration,
        prompt_influence=args.prompt_influence,
        loop=args.loop,
        model_id=args.model_id,
        output_dir=args.output_dir,
    ))
    return _emit(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(prog="tools_cli", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="Stream INFO logs to stdout as well.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("get_asset", help="Fetch a batch of assets (max 10).")
    p.add_argument("--payload", required=True,
                   help='JSON file: {"assets":[{"name","description","asset_type","keywords","asset_id"}], "art_style","output_path"}')
    p.set_defaults(func=cmd_get_asset)

    p = sub.add_parser("describe_images", help="Describe images fetched from URLs.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--urls", help="Comma-separated URL list.")
    g.add_argument("--urls-file", help='JSON file: ["url1", ...] or {"urls": [...]}.')
    p.set_defaults(func=cmd_describe_images)

    p = sub.add_parser("svg_path", help="Generate an SVG d-attribute for a predefined equation.")
    p.add_argument("--equation", required=True,
                   help="PARABOLIC | CIRCULAR | ELLIPTICAL | SINE_WAVE | SPIRAL | S_CURVE | LINEAR | ARC | BEZIER | ZIGZAG | BOUNCE | SPLINE")
    p.add_argument("--params-json", required=True, help="JSON string of named params for the equation.")
    p.set_defaults(func=cmd_svg_path)

    p = sub.add_parser("merge_paths", help="Merge multiple SVG d-attribute paths into one.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--paths-json", help='JSON string: ["d1", "d2", ...].')
    g.add_argument("--paths-file", help='JSON file: ["d1", ...] or {"paths": [...]}.')
    p.set_defaults(func=cmd_merge_paths)

    p = sub.add_parser("validate_json", help="Validate a JSON file.")
    p.add_argument("--file", required=True, help="Path to the JSON file.")
    p.add_argument("--topic", help="If given and JSON is valid, also write it to Outputs/{topic}/Direction/Latest/latest.json.")
    p.set_defaults(func=cmd_validate_json)

    p = sub.add_parser("validate_tsx", help="Validate a batch of TSX scene components.")
    p.add_argument("--payload", required=True,
                   help='JSON file: {"components":[{"tsx_content","output_path"|"scene_index"}], "total_frames":600, "topic":"..."}')
    p.add_argument("--topic", help="Topic ID used to derive output_path from scene_index when not set explicitly.")
    p.set_defaults(func=cmd_validate_tsx)

    p = sub.add_parser("validate_script_with_emotions",
                       help="Validate an emotion-tagged script against the original.")
    p.add_argument("--file", required=True, help="Path to the tagged script.")
    p.add_argument("--topic", required=True, help="Topic ID; used to locate the original script.")
    p.set_defaults(func=cmd_validate_script_with_emotions)

    p = sub.add_parser("generate_sound_effect", help="Generate a sound effect via ElevenLabs and save it locally.")
    p.add_argument("--text", required=True, help="Prompt describing the sound.")
    p.add_argument("--duration", type=float, default=None, help="Target duration in seconds (0.5-30).")
    p.add_argument("--prompt-influence", type=float, default=0.3, help="0..1, defaults to 0.3.")
    p.add_argument("--loop", action="store_true", help="Request a loop-friendly sample.")
    p.add_argument("--model-id", default="eleven_text_to_sound_v2", help="ElevenLabs model id.")
    p.add_argument("--output-dir", default=None, help="Directory to save the generated MP3 into. Defaults to CWD.")
    p.set_defaults(func=cmd_generate_sound_effect)

    args = parser.parse_args()
    set_console_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
