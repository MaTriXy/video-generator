"""
Initialize manifest with creator name and mark init as completed.
Usage: python -m scripts.init.init_manifest <creator_name>
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.controllers.manifest_controller import ManifestController


def init_manifest(creator_name: str) -> bool:
    manifest = ManifestController()

    # Add creator_name to metadata
    manifest.manifest_json['metadata']['creator_name'] = creator_name

    # Set init_completed to true
    manifest.manifest_json['init_completed'] = True

    # Save the manifest
    success = manifest.io_controller.write_json(manifest.manifest_path, manifest.manifest_json)

    if success:
        print(f"Manifest initialized with creator_name: {creator_name}")
        print("init_completed set to true")
    else:
        print("Failed to initialize manifest")

    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.init.init_manifest <creator_name>")
        sys.exit(1)

    creator_name = sys.argv[1]
    success = init_manifest(creator_name)
    sys.exit(0 if success else 1)
