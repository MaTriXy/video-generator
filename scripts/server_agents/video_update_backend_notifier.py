import json
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from scripts.server_agents.claude_sdk_config import (
    VIDEO_GEN_API_BASE_URL,
    VIDEO_GENERATION_UPDATE_ENDPOINT,
)
from scripts.logging_config import get_service_logger

logger = get_service_logger("video_update_backend_notifier")
from scripts.utility.config import OUTSCAL_SERVER_KEY


def strip_v2_suffix(video_id: Optional[str]) -> Optional[str]:
    if video_id and video_id.endswith("-v2"):
        return video_id[:-3]
    return video_id


async def _send_notification(
    payload: Dict[str, Any],
    video_id: str,
    step: str,
    label: str,
) -> Dict[str, Any]:
    url = f"{VIDEO_GEN_API_BASE_URL}{VIDEO_GENERATION_UPDATE_ENDPOINT}"

    log_payload = {k: v for k, v in payload.items() if k != "key"}
    logger.info(f"Sending {label} to {url}: {json.dumps(log_payload)}", extra={"video_id": video_id, "step": step})

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_data = await response.json()
                if response.status == 200:
                    logger.info(f"{label} notification delivered (status={response.status}): {json.dumps(response_data)}", extra={"video_id": video_id, "step": step})
                else:
                    logger.error(f"{label} notification rejected (status={response.status}): {json.dumps(response_data)}", extra={"video_id": video_id, "step": step})
                return {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "response": response_data,
                }
    except aiohttp.ClientError as e:
        logger.error(f"{label} API request failed: {e}", exc_info=True, extra={"video_id": video_id, "step": step})
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error sending {label} notification: {e}", exc_info=True, extra={"video_id": video_id, "step": step})
        return {"success": False, "error": str(e)}

NOTIFIABLE_STEPS = {"code","assets","audio","direction"}


async def send_update_to_backend(
    video_id: str,
    step: str,
    output_files: Optional[list] = None,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    transcript_path: Optional[str] = None,
    custom_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if step.lower() not in NOTIFIABLE_STEPS:
        logger.info(f"Skipping backend notification for step={step} (only {NOTIFIABLE_STEPS} are notified)", extra={"video_id": video_id, "step": step})
        return {"success": True, "skipped": True}

    resolved_agent_id = agent_id
    if not resolved_agent_id and transcript_path:
        resolved_agent_id = Path(transcript_path).stem.replace("agent-", "")

    payload = {
        "status": "completed",
        "sessionId": session_id,
        "video_id": strip_v2_suffix(video_id),
        "output_files": output_files or [],
        "agentId": resolved_agent_id,
        "step": step.lower(),
        "key": OUTSCAL_SERVER_KEY,
    }
    if custom_data:
        payload["customData"] = custom_data

    return await _send_notification(payload, video_id, step, "SUCCESS")


async def send_failure_to_backend(
    video_id: str,
    step_type: str,
    error_message: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "status": "failed",
        "sessionId": session_id,
        "video_id": strip_v2_suffix(video_id),
        "output_files": [],
        "agentId": step_type,
        "step": step_type.lower(),
        "key": OUTSCAL_SERVER_KEY,
        "customData": {
            "error": error_message,
            "failed_at": datetime.now().isoformat(),
        },
    }

    return await _send_notification(payload, video_id, step_type, "FAILURE")
