import shutil
from pathlib import Path

from scripts.path_setup import PROJECT_ROOT as project_root
from scripts.logging_config import get_service_logger

logger = get_service_logger("prompt_utils")


def cleanup_prompts(topic_id: str, step_name: str) -> None:
    prompts_base = project_root / "Outputs" / "Prompts"
    for sub in ("active", "claimed"):
        target = prompts_base / sub / topic_id / step_name
        if target.exists():
            shutil.rmtree(str(target), ignore_errors=True)
            logger.info(f"Cleaned up {sub} prompts: {target}", extra={"video_id": topic_id, "step": step_name})
            parent = target.parent
            try:
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass
