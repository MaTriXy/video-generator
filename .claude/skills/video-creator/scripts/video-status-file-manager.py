#!/usr/bin/env python3
"""Video Creation Status Manager"""

import json
import sys
import os
from pathlib import Path

STEP_CONFIG = {
    "user-input": {"reference_file": "user-input.md", "order": 1},
    "audio": {"reference_file": "audio.md", "order": 2},
    "direction": {"reference_file": "direction.md", "order": 3},
    "asset-generator": {"reference_file": "asset-generator.md", "order": 4},
    "design": {"reference_file": "design.md", "order": 5},
    "coding": {"reference_file": "coding.md", "order": 6}
}


def get_step_order():
    return sorted(STEP_CONFIG.keys(), key=lambda x: STEP_CONFIG[x]["order"])


def get_paths(topic, base_dir="Outputs"):
    skill_dir = Path(__file__).parent.parent
    return {
        "status_file": Path(base_dir) / topic / "video-status.json",
        "template": skill_dir / "templates" / "video-status-template.json",
        "references": skill_dir / "references"
    }


def create_status_file(topic, base_dir="Outputs"):
    paths = get_paths(topic, base_dir)

    with open(paths["template"], 'r', encoding='utf-8') as f:
        status_data = json.load(f)

    status_data["topic"] = topic
    status_data["steps"]["user-input"]["status"] = "completed"

    paths["status_file"].parent.mkdir(parents=True, exist_ok=True)

    with open(paths["status_file"], 'w', encoding='utf-8') as f:
        json.dump(status_data, f, indent=2)

    print(json.dumps({"success": True, "file": str(paths["status_file"])}))


def check_file_exists(topic, base_dir="Outputs"):
    paths = get_paths(topic, base_dir)

    if not paths["status_file"].exists():
        print(json.dumps({"exists": False}))
    else:
        print(json.dumps({"exists": True, "file": str(paths["status_file"])}))


def complete_step(topic, step_id, base_dir="Outputs"):
    paths = get_paths(topic, base_dir)

    if not paths["status_file"].exists():
        print(json.dumps({"error": "Status file not found"}))
        sys.exit(1)

    with open(paths["status_file"], 'r', encoding='utf-8') as f:
        status_data = json.load(f)

    status_data["steps"][step_id]["status"] = "completed"

    step_order = get_step_order()
    current_index = step_order.index(step_id)

    if current_index + 1 < len(step_order):
        next_step_id = step_order[current_index + 1]
        status_data["steps"][next_step_id]["status"] = "in_progress"

        with open(paths["status_file"], 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2)

        result = {
            "step_id": next_step_id
        }
        print(json.dumps(result, indent=2))
    else:
        with open(paths["status_file"], 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2)

        print(json.dumps({"completed": True, "message": "All steps completed"}))


def get_next_step(topic, base_dir="Outputs"):
    paths = get_paths(topic, base_dir)

    if not paths["status_file"].exists():
        print(json.dumps({"error": "Status file not found"}))
        sys.exit(1)

    with open(paths["status_file"], 'r', encoding='utf-8') as f:
        status_data = json.load(f)

    for step_id in get_step_order():
        if status_data["steps"][step_id]["status"] in ["in_progress", "pending"]:
            result = {
                "step_id": step_id
            }
            print(json.dumps(result, indent=2))
            return

    print(json.dumps({"completed": True, "message": "All steps completed"}))


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["create-video-status-file", "check-if-file-exist", "complete-step", "get-next-step"], required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--step")
    parser.add_argument("--base-dir", default="Outputs")

    args = parser.parse_args()

    if args.action == "create-video-status-file":
        create_status_file(args.topic, args.base_dir)
    elif args.action == "check-if-file-exist":
        check_file_exists(args.topic, args.base_dir)
    elif args.action == "complete-step":
        if not args.step:
            print(json.dumps({"error": "--step required"}))
            sys.exit(1)
        complete_step(args.topic, args.step, args.base_dir)
    elif args.action == "get-next-step":
        get_next_step(args.topic, args.base_dir)


if __name__ == "__main__":
    main()
