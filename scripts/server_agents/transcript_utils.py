import os
import json
from typing import Optional, Dict, Any, List

from scripts.logging_config import get_service_logger

logger = get_service_logger("transcript_utils")


def read_jsonl(filepath: str) -> Optional[List[Dict[str, Any]]]:
    try:
        normalized_path = os.path.normpath(filepath)
        objects = []
        with open(normalized_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    objects.append(json.loads(line))
        return objects
    except Exception as e:
        logger.error(f"Failed to read JSONL file {filepath}: {e}", exc_info=True, extra={"video_id": "--", "step": "--"})
        return None


def find_transcript_file(session_id: str) -> Optional[str]:
    claude_projects_dir = os.path.expanduser('~/.claude/projects')

    if not os.path.exists(claude_projects_dir):
        return None

    session_filename = f"{session_id}.jsonl"

    for project_dir in os.listdir(claude_projects_dir):
        transcript_path = os.path.join(claude_projects_dir, project_dir, session_filename)
        if os.path.exists(transcript_path):
            return transcript_path

    return None
