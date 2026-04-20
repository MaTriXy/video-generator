import json
from typing import Optional, Dict, Any

from scripts.path_setup import PROJECT_ROOT as project_root
from scripts.server_agents.claude_sdk_config import get_postprocessing_class, ASSET_CONFIG
from scripts.server_agents.video_update_backend_notifier import send_update_to_backend, send_failure_to_backend
from scripts.server_agents.prompt_utils import cleanup_prompts
from scripts.enums import AssetType
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.gen_metadata_controller import GenMetadataController
from scripts.logging_config import get_agent_logger

logger = get_agent_logger("agent_completion_handler")


def _cleanup_claimed_prompts(topic_id: str, asset_type: AssetType) -> None:
    step_name = ASSET_CONFIG.get(asset_type, {}).get("step_name")
    if not step_name:
        return
    cleanup_prompts(topic_id, step_name)


def _get_output_files(video_id: str, asset_type: str) -> Optional[list]:
    try:
        manifest_controller = ManifestController()
        manifest_controller.set_topic(video_id)
        asset_enum = AssetType(asset_type)
        version = manifest_controller.get_current_gen_version(asset_enum)
        output_dir = project_root / "Outputs" / video_id / asset_type / f"v{version}"
        if not output_dir.exists():
            return None
        files = [str(f.resolve()) for f in output_dir.iterdir() if f.is_file()]
        return files if files else None
    except Exception as e:
        logger.error(f"Failed to get output files: {e}", exc_info=True, extra={"video_id": video_id, "step": asset_type})
        return None


async def run_postprocessing(video_id: str, asset_type: Optional[str]) -> Optional[list]:
    if not video_id or not asset_type:
        raise ValueError(f"Missing required parameters: video_id={video_id}, asset_type={asset_type}")

    asset_enum = AssetType(asset_type)
    postprocess_class = get_postprocessing_class(asset_enum)
    if not postprocess_class:
        raise ValueError(f"No postprocessing class found for asset type: {asset_type}")

    logger.info(f"Running postprocessing for {asset_type}...", extra={"video_id": video_id, "step": asset_type})
    postprocessor = postprocess_class(topic=video_id)
    success, result = await postprocessor.run()

    if not success:
        error_msg = result if isinstance(result, str) else f"Postprocessing returned failure for {asset_type}"
        raise RuntimeError(error_msg)

    logger.info(f"Postprocessing completed for {asset_type}", extra={"video_id": video_id, "step": asset_type})
    output_files = _get_output_files(video_id, asset_type)
    return output_files


def _build_custom_data(
    video_id: str,
    topic_id: str,
    asset_type: str,
    agent_label: str,
    cost_usd: Optional[float],
    duration_ms: Optional[float],
    usage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    custom_data = {}
    manifest_controller = ManifestController()
    manifest_controller.set_topic(topic_id)

    if asset_type.lower() == "audio":
        try:
            transcript_file = project_root / "Outputs" / topic_id / "Transcript" / "latest.json"
            if transcript_file.exists():
                with open(transcript_file, "r", encoding="utf-8") as f:
                    words = json.load(f)
                if words:
                    custom_data["audioDuration"] = words[-1]["end_ms"] / 1000
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}", extra={"video_id": video_id, "step": agent_label})
        try:
            gen_meta = GenMetadataController(topic_id, AssetType.AUDIO, manifest_controller)
            audio_meta = gen_meta.read_metadata().get(AssetType.AUDIO.value, {})
            custom_data["audioModel"] = audio_meta.get("model_used")
            tts_char_count = audio_meta.get("tts_char_count")
            if tts_char_count is not None:
                custom_data["ttsCharCount"] = tts_char_count
        except Exception as e:
            logger.error(f"Failed to get audio model: {e}", extra={"video_id": video_id, "step": agent_label})
    elif asset_type.lower() == "video":
        try:
            metadata = manifest_controller.get_metadata()
            if metadata and metadata.get("totalFrames"):
                custom_data["totalFrames"] = metadata.get("totalFrames")
        except Exception as e:
            logger.error(f"Failed to get total frames: {e}", extra={"video_id": video_id, "step": agent_label})
    elif asset_type.lower() == "assets":
        try:
            assets_manifest = manifest_controller.get_field(AssetType.ASSETS)
            assets_path = assets_manifest.get('path') if assets_manifest else None
            if assets_path:
                assets_file = project_root / assets_path
                if assets_file.exists():
                    with open(assets_file, "r", encoding="utf-8") as f:
                        assets_data = json.load(f)
                    custom_data["assets"] = assets_data["assets"]
        except Exception as e:
            logger.error(f"Failed to get assets data: {e}", extra={"video_id": video_id, "step": agent_label})

    summary = {}
    if cost_usd is not None:
        summary["api_cost_usd"] = cost_usd
    if duration_ms is not None:
        summary["agent_run_secs"] = round(duration_ms / 1000, 2)
    if usage and isinstance(usage, dict):
        if "output_tokens" in usage:
            summary["output_tokens"] = usage["output_tokens"]
        if "cache_creation_input_tokens" in usage:
            summary["cache_creation_tokens"] = usage["cache_creation_input_tokens"]
        if "cache_read_input_tokens" in usage:
            summary["cache_read_tokens"] = usage["cache_read_input_tokens"]
    if summary:
        custom_data["summary"] = summary

    return custom_data


async def send_step_completion(
    video_id: str,
    step_type: str,
    asset_type: AssetType,
    agent_label: str,
    session_id: Optional[str],
    agent_id: Optional[str],
    transcript_path: Optional[str],
    cost_usd: Optional[float],
    duration_ms: Optional[float],
    usage: Optional[Dict[str, Any]] = None,
) -> None:
    topic_id = f"{video_id}-v2"
    asset_type_value = asset_type.value

    try:
        try:
            output_files = await run_postprocessing(topic_id, asset_type_value)
        except Exception as e:
            logger.error(f"Postprocessing failed: {e}", exc_info=True, extra={"video_id": video_id, "step": agent_label})
            await send_failure_to_backend(video_id, step_type, f"Postprocessing failed: {e}")
            return

        custom_data = _build_custom_data(
            video_id=video_id,
            topic_id=topic_id,
            asset_type=asset_type_value,
            agent_label=agent_label,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            usage=usage,
        )

        try:
            api_response = await send_update_to_backend(
                video_id=topic_id,
                step=step_type,
                output_files=output_files,
                session_id=session_id,
                agent_id=agent_id,
                transcript_path=transcript_path,
                custom_data=custom_data,
            )
            if not api_response.get("success"):
                logger.error(f"Backend notification failed: {api_response.get('error')}", extra={"video_id": video_id, "step": agent_label})
        except Exception as e:
            logger.error(f"Failed to send completion callback: {e}", exc_info=True, extra={"video_id": video_id, "step": agent_label})
    finally:
        _cleanup_claimed_prompts(topic_id, asset_type)
