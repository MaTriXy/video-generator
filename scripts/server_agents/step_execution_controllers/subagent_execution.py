"""
SubagentExecution — Sonnet orchestrator that spawns Opus subagents via Task tool.
Used for: Code, Assets, Audio.
"""

import shutil
from pathlib import Path
from typing import Optional, List, Union

from claude_agent_sdk.types import HookMatcher

from scripts.path_setup import PROJECT_ROOT as project_root
from scripts.enums import AssetType
from scripts.server_agents.base_persistent_agent import (
    BasePersistentAgent,
    PROMPTS_DIR,
    logger,
)
from scripts.server_agents.claude_sdk_config import get_tools
from scripts.server_agents.subagent_stop_controller import handle_subagent_stop


def _read_prompt_template(rel_path: str) -> str:
    """Read a prompt .md file from the prompts/ submodule."""
    path = PROMPTS_DIR / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


class SubagentExecution(BasePersistentAgent):

    def __init__(self, asset_type: AssetType):
        super().__init__(asset_type)

    def _write_active_prompts(self, topic_id: str, prompt_result: Union[str, List[str]]) -> None:
        prompts_base = project_root / "Outputs" / "Prompts"
        active_dir = prompts_base / "active" / topic_id / self.step_name

        active_dir.mkdir(parents=True, exist_ok=True)

        paths = [prompt_result] if isinstance(prompt_result, str) else prompt_result
        for path_str in paths:
            src = Path(path_str)
            if not src.is_absolute():
                src = project_root / src
            if not src.exists():
                raise FileNotFoundError(f"Prompt file not found: {src}")
            dest = active_dir / src.name
            shutil.copy2(str(src), str(dest))
            logger.info(f"Copied prompt to active: {dest}", extra={"video_id": topic_id, "step": self.agent_label})

    def _get_system_prompt(self) -> str:
        template = _read_prompt_template("orchestrator/system-prompt.md")
        return template.replace("{{subagent_name}}", self.subagent_name)

    def _get_tools(self) -> list:
        return get_tools(self.asset_type) + ["Task"]

    def _get_hooks(self) -> dict:
        return {
            "SubagentStop": [HookMatcher(matcher="", hooks=[self._create_subagent_hook()])]
        }

    def _create_subagent_hook(self):
        async def hook(input_data, matched, context):
            result = await handle_subagent_stop(input_data, matched, context)
            transcript_path = input_data.get("agent_transcript_path")
            if transcript_path:
                self._last_subagent_agent_id = Path(transcript_path).stem.replace("agent-", "")
            return result
        return hook

    def _get_extra_args(self) -> dict:
        return {"disable-slash-commands": None}

    def _build_query_prompt(self, video_id: str, prompt_result: Union[str, List[str]]) -> str:
        """Write active prompts and build query from single/multi templates."""
        topic_id = f"{video_id}-v2"
        self._write_active_prompts(topic_id, prompt_result)

        prompt_count = len(prompt_result) if isinstance(prompt_result, list) else 1
        if prompt_count == 1:
            template = _read_prompt_template("orchestrator/query-prompt-single.md")
        else:
            template = _read_prompt_template("orchestrator/query-prompt-multi.md")

        return (
            template
            .replace("{{subagent_name}}", self.subagent_name)
            .replace("{{step_name}}", self.step_name)
            .replace("{{prompt_count}}", str(prompt_count))
            .replace("{{video_id}}", video_id)
        )

    def _build_resume_prompt(self, agent_id: str, resume_prompt: Optional[str] = None) -> str:
        prompt = f'Resume the subagent with ID "{agent_id}" using the Task tool with resume="{agent_id}".'
        if resume_prompt:
            prompt += f' Pass it this prompt: {resume_prompt}'
        return prompt
