"""
MainAgentExecution — Agent that performs work directly without spawning subagents.
Used for: Direction, Assets, Audio steps (Opus does the work itself).
System prompt loaded via system-prompt-file; preprocessed prompt content passed as query.
"""

from pathlib import Path
from typing import Optional, List, Union

from scripts.path_setup import PROJECT_ROOT as project_root
from scripts.enums import AssetType
from scripts.server_agents.base_persistent_agent import BasePersistentAgent, PROMPTS_DIR

SYSTEM_PROMPT_FILES = {
    AssetType.DIRECTION: "system-prompt-direction.md",
    AssetType.ASSETS: "system-prompt-asset.md",
    AssetType.AUDIO: "system-prompt-audio.md",
}


class MainAgentExecution(BasePersistentAgent):

    def __init__(self, asset_type: AssetType):
        super().__init__(asset_type)

    def _get_extra_args(self) -> dict:
        prompt_file = SYSTEM_PROMPT_FILES.get(self.asset_type)
        return {
            "disable-slash-commands": None,
            "system-prompt-file": str(PROMPTS_DIR / "orchestrator" / prompt_file),
        }

    def _build_query_prompt(self, video_id: str, prompt_result: Union[str, List[str]]) -> str:
        """Read the preprocessed prompt file content directly and return it as the query."""
        path = Path(prompt_result) if isinstance(prompt_result, str) else Path(prompt_result[0])
        if not path.is_absolute():
            path = project_root / path
        return path.read_text(encoding="utf-8")

    def _build_resume_prompt(self, agent_id: str, resume_prompt: Optional[str] = None) -> str:
        prompt = "Continue working."
        if resume_prompt:
            prompt += f" Additional instructions: {resume_prompt}"
        return prompt
