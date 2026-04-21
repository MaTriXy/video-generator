"""
Loads MCP asset agent prompts from the centralized prompts directory.
Caches with mtime check — picks up edits live without restart.
"""

import json
import os
from pathlib import Path

_MCP_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPTS_FILE = _MCP_ROOT.parent / "prompts" / "orchestrator" / "mcp-asset-prompts.json"

_cached_mtime: float = 0
_cached_data: dict = {}


def _load() -> dict:
    global _cached_mtime, _cached_data
    mtime = os.path.getmtime(_PROMPTS_FILE)
    if mtime != _cached_mtime:
        _cached_data = json.loads(_PROMPTS_FILE.read_text(encoding="utf-8"))
        _cached_mtime = mtime
    return _cached_data


def get_mcp_prompt(agent_name: str, **kwargs) -> str:
    """Get a prompt by agent name, with optional variable substitution."""
    prompt = _load()[agent_name]
    if kwargs:
        prompt = prompt.format(**kwargs)
    return prompt
