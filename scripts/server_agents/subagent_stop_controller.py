import os
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from claude_agent_sdk.types import SubagentStopHookInput, HookContext

from dotenv import load_dotenv
load_dotenv()

from scripts.server_agents.transcript_utils import read_jsonl
from scripts.server_agents.subagent_transcript_controller import (
    save_subagent_logs,
    find_first_read_path,
)
from scripts.server_agents.claude_sdk_config import get_asset_type_for_step, get_config
from scripts.logging_config import get_service_logger

logger = get_service_logger("subagent_stop_controller")


@dataclass
class SubagentCompletionInfo:
    video_id: Optional[str]
    batch_label: Optional[str]
    asset_type: Optional[str]
    session_id: Optional[str]
    prompt_path: Optional[str]


def _step_to_folder(step_type: str) -> str:
    try:
        asset_type = get_asset_type_for_step(step_type)
        return get_config(asset_type)["output_folder"]
    except (ValueError, KeyError):
        return step_type


def parse_prompt_path(file_path: str) -> Dict[str, Any]:
    result = {
        "video_id": None,
        "batch_label": None,
        "asset_type": None,
        "version": None,
    }

    if not file_path:
        return result

    normalized_path = file_path.replace("\\", "/")

    filename = os.path.basename(file_path)
    # Match batch prompts like prompt_0_7.md or single prompts like prompt_3.md
    batch_match = re.search(r'prompt_(\d+_\d+)', filename)
    if batch_match:
        result["batch_label"] = batch_match.group(1)
    else:
        single_match = re.search(r'(?:prompt_|scene_)(\d+)', filename)
        if single_match:
            result["batch_label"] = single_match.group(1)

    # Check for claimed prompt path: Prompts/claimed/{topic_id}/{step_type}/
    if "Prompts/claimed/" in normalized_path:
        after_claimed = normalized_path.split("Prompts/claimed/")[1]
        parts = after_claimed.split("/")
        if len(parts) > 0:
            result["video_id"] = parts[0]
        if len(parts) > 1:
            step_type = parts[1]
            result["asset_type"] = _step_to_folder(step_type)
    elif "Outputs/" in normalized_path:
        after_outputs = normalized_path.split("Outputs/")[1]
        parts = after_outputs.split("/")
        if len(parts) > 0:
            result["video_id"] = parts[0]
        if len(parts) > 1:
            result["asset_type"] = parts[1]
        if len(parts) > 2:
            version_match = re.match(r'v(\d+)', parts[2])
            if version_match:
                result["version"] = int(version_match.group(1))
    elif "Prompts/" in normalized_path:
        after_prompts = normalized_path.split("Prompts/")[1]
        parts = after_prompts.split("/")
        if len(parts) > 0:
            result["video_id"] = parts[0]
        if len(parts) > 1:
            result["asset_type"] = parts[1]

    return result


def build_completion_info(
    input_data: SubagentStopHookInput,
    transcript_data: Optional[list]
) -> SubagentCompletionInfo:
    session_id = input_data.get("session_id")
    prompt_path = None
    parsed = {
        "video_id": None,
        "batch_label": None,
        "asset_type": None,
        "version": None,
    }

    if transcript_data:
        prompt_path = find_first_read_path(transcript_data)
        if prompt_path:
            parsed = parse_prompt_path(prompt_path)

    return SubagentCompletionInfo(
        video_id=parsed["video_id"],
        batch_label=parsed["batch_label"],
        asset_type=parsed["asset_type"],
        session_id=session_id,
        prompt_path=prompt_path,
    )


async def handle_subagent_stop(
    input_data: SubagentStopHookInput,
    matched: str | None,
    context: HookContext
) -> Dict[str, Any]:
    session_id = input_data.get("session_id")
    cwd = input_data.get("cwd")
    transcript_path = input_data.get("agent_transcript_path")

    result = {
        "continue": True,
        "session_id": session_id,
        "cwd": cwd,
        "transcript_path": transcript_path,
        "video_id": None,
        "batch_label": None,
        "asset_type": None,
        "api_response": None,
    }

    transcript_data = None
    if transcript_path:
        transcript_data = read_jsonl(transcript_path)

    completion_info = build_completion_info(input_data, transcript_data)

    result["video_id"] = completion_info.video_id
    result["batch_label"] = completion_info.batch_label
    result["asset_type"] = "code" if completion_info.asset_type == "Video" else completion_info.asset_type
    result["prompt_path"] = completion_info.prompt_path

    vid = result.get('video_id') or '--'
    stype = result.get('asset_type') or '--'

    if not result['asset_type']:
        logger.warning(f"Subagent stopped but could not identify asset_type: session={session_id}, prompt_path={completion_info.prompt_path}", extra={"video_id": vid, "step": "--"})

    if result['asset_type']:
        logger.info(
            f"Subagent stopped: session={session_id}, video={vid}, asset={stype}, batch={result['batch_label']}",
            extra={"video_id": vid, "step": stype}
        )
        try:
            first_ts = transcript_data[0].get("timestamp")
            last_ts = transcript_data[-1].get("timestamp")
            if first_ts and last_ts:
                start_time = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                duration = (end_time - start_time).total_seconds()
                minutes, seconds = divmod(int(duration), 60)
                logger.info(f"Duration: {minutes}m {seconds}s (start: {first_ts}, end: {last_ts})", extra={"video_id": vid, "step": stype})
        except Exception as e:
            logger.warning(f"Could not calculate duration: {e}", extra={"video_id": vid, "step": stype})

    if transcript_data and completion_info.video_id and completion_info.asset_type:
        save_subagent_logs(
            transcript_path,
            completion_info.video_id,
            completion_info.asset_type,
            transcript_data,
            completion_info.batch_label
        )

    return result
