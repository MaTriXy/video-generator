import json
from typing import Optional, Dict, Any
from datetime import datetime

from scripts.path_setup import PROJECT_ROOT as project_root

from scripts.controllers.manifest_controller import ManifestController
from scripts.enums import AssetType
from scripts.logging_config import get_service_logger

logger = get_service_logger("subagent_transcript_controller")


def save_subagent_logs(
    transcript_path: str,
    video_id: str,
    asset_type: str,
    transcript_data: list,
    batch_label: Optional[str] = None
) -> Optional[str]:
    if not video_id or not asset_type or not transcript_data:
        return None

    try:
        manifest_controller = ManifestController()
        manifest_controller.set_topic(video_id)
        asset_enum = AssetType(asset_type)
        version = manifest_controller.get_current_gen_version(asset_enum)

        log_dir = project_root / "Outputs" / video_id / asset_type / f"v{version}" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if batch_label is not None:
            log_file = log_dir / f"subagent_batch_{batch_label}_{timestamp}.json"
        else:
            log_file = log_dir / f"subagent_{timestamp}.json"

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved subagent logs to: {log_file}", extra={"video_id": video_id, "step": asset_type})
        return str(log_file)
    except Exception as e:
        logger.error(f"Failed to save subagent logs: {e}", exc_info=True, extra={"video_id": video_id, "step": asset_type})
        return None


def find_first_read_path(transcript_data: list) -> Optional[str]:
    for entry in transcript_data:
        if not isinstance(entry, dict):
            continue

        content = entry.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue

        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Read":
                file_path = item.get("input", {}).get("file_path")
                if file_path and "Prompts" in file_path:
                    return file_path

    return None
