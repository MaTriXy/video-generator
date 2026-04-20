"""
Prompt Cache Controller — Local File Reader

Reads prompts from the local prompts/ submodule.
Each prompt is a pair of files:
  <prompts_dir>/<prompt_name>.md            — the prompt text
  <prompts_dir>/<prompt_name>.config.json   — config dict (optional)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.logging_config import get_utility_logger

# Initialize logger
logger = get_utility_logger('controllers.prompt_cache')

class PromptCacheController:

    def __init__(self):
        self.prompts_dir = project_root / "prompts"
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
        else:
            logger.info(f"PromptCacheController initialized — prompts_dir: {self.prompts_dir}")

    def fetch_prompt(self, prompt_name: str, tag: Optional[str] = "production") -> Dict[str, Any]:
        """
        Read a prompt from local files.

        Args:
            prompt_name: Slash-separated name, e.g. "Course-Creation/Video/Director/Direction-Creation-Prompt-Modular"
            tag: Ignored (kept for API compatibility).

        Returns:
            Dict with keys: name, tag, prompt, config, version, labels, type
        """
        md_path = self.prompts_dir / f"{prompt_name}.md"

        if not md_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {md_path}  (prompt_name={prompt_name!r})"
            )

        prompt_text = md_path.read_text(encoding="utf-8").strip()

        # Read optional .config.json
        config_path = self.prompts_dir / f"{prompt_name}.config.json"
        config: Dict[str, Any] = {}
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file {config_path}: {e}")

        logger.info(f"Fetched prompt from local file: {prompt_name}")

        return {
            "name": prompt_name,
            "tag": tag or "latest",
            "prompt": prompt_text,
            "config": config,
            "version": None,
            "labels": [],
            "type": "text",
        }
