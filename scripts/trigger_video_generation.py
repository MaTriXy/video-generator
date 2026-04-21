import requests
import sys
import json
import glob
import os

VIDEO_ID = "69c2a155c278fc5cea308b5f"
SERVER_URL = "http://127.0.0.1:3100"
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "Outputs")


def find_output_dir():
    """Find the output directory for the current VIDEO_ID."""
    pattern = os.path.join(OUTPUTS_DIR, f"{VIDEO_ID}*")
    matches = sorted(glob.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No output directory found for {VIDEO_ID}")
    return matches[-1]


def find_latest_direction_version(output_dir):
    """Scan the Direction folder and return the highest version number."""
    direction_dir = os.path.join(output_dir, "Direction")
    version_dirs = glob.glob(os.path.join(direction_dir, "v*"))
    versions = []
    for d in version_dirs:
        dirname = os.path.basename(d)
        if dirname.startswith("v") and dirname[1:].isdigit():
            versions.append(int(dirname[1:]))
    if not versions:
        raise FileNotFoundError(f"No direction versions found in {direction_dir}")
    return max(versions)


def sync_scripts_from_direction(output_dir):
    """Read latest direction, update manifest and sync audioTranscriptPortion to script files."""
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Find the actual latest direction version from disk
    direction_version = find_latest_direction_version(output_dir)
    direction_path = os.path.join(
        output_dir, "Direction", f"v{direction_version}", f"Direction-v{direction_version}.json"
    )

    with open(direction_path, "r") as f:
        direction = json.load(f)

    # Collect audioTranscriptPortion from all scenes
    transcript_parts = []
    for scene in direction["scenes"]:
        portion = scene.get("audioTranscriptPortion", "")
        if portion:
            transcript_parts.append(portion)
    full_transcript = " ".join(transcript_parts)

    # Update manifest Direction entry with latest version/path
    relative_direction_path = os.path.relpath(direction_path, os.path.join(output_dir, "..")).replace("\\", "/")
    manifest["Direction"]["version"] = direction_version
    manifest["Direction"]["current_gen_version"] = direction_version
    manifest["Direction"]["path"] = "Outputs/"+relative_direction_path

    # Update manifest metadata from direction
    if "totalFrames" in direction:
        manifest["metadata"]["totalFrames"] = direction["totalFrames"]
    manifest["metadata"]["totalScenes"] = len(direction["scenes"])

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Updated manifest.json with direction v{direction_version} metadata")

    # Write transcript to both script files
    script_path = os.path.join(output_dir, "Scripts", "script.md")
    script_user_input_path = os.path.join(output_dir, "Scripts", "script-user-input.md")

    for path in [script_path, script_user_input_path]:
        with open(path, "w") as f:
            f.write(full_transcript)
        print(f"Updated {os.path.basename(path)} with audioTranscriptPortion from direction v{direction_version}")


def trigger(step_type: str):
    if step_type == "audio":
        output_dir = find_output_dir()
        sync_scripts_from_direction(output_dir)

    url = f"{SERVER_URL}/video-generation"
    payload = {
        "video_id": VIDEO_ID,
        "step_type": step_type,
    }
    print(f"Calling {url} with step_type={step_type}, video_id={VIDEO_ID}")
    resp = requests.post(url, json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trigger_video_generation.py <step_type>")
        print("Allowed steps: direction, code, assets, audio")
        sys.exit(1)
    trigger(sys.argv[1])
