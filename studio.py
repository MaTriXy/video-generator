#!/usr/bin/env python3
"""Launch Remotion Studio for an OVG topic on any OS.

Usage:
    python studio.py <topic>
    python studio.py binary-search-tree-v2
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Open Remotion Studio for an OVG topic.")
    parser.add_argument("topic", help="Topic id, e.g. binary-search-tree-v2")
    args = parser.parse_args()

    studio_dir = Path(__file__).resolve().parent / "studio"
    if not studio_dir.is_dir():
        print(f"studio/ not found at {studio_dir}", file=sys.stderr)
        return 1

    env = {**os.environ, "OVG_TOPIC": args.topic}
    print(f"[{sys.platform}] OVG_TOPIC={args.topic}  ->  npm run studio  (cwd={studio_dir})")

    try:
        return subprocess.run(
            ["npm", "run", "studio"],
            cwd=studio_dir,
            env=env,
            shell=(os.name == "nt"),
        ).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
