import os
from pathlib import Path
from scripts.enums import AssetType
from scripts.server_agents.execution_types import ExecutionType
from scripts.path_setup import PROMPTS_DIR
from scripts.utility.config import (
    BASIC_CLAUDE_CODE_TOKEN,
    CODE_CLAUDE_CODE_TOKEN,
)


VIDEO_GEN_API_BASE_URL = os.environ.get("VIDEO_GEN_API_URL", "http://localhost:3012/api")
VIDEO_GENERATION_UPDATE_ENDPOINT = "/internal/video-generation/updates"

from scripts.claude_cli.content_video_direction.pre_process import VideoDirectionPreProcess
from scripts.claude_cli.content_video.pre_process import VideoPreProcess
from scripts.claude_cli.asset_generator.pre_process import AssetGeneratorPreProcess
from scripts.claude_cli.content_audio.pre_process import AudioPreProcess

from scripts.claude_cli.content_video_direction.post_process import VideoDirectionPostProcessing
from scripts.claude_cli.content_video.post_process import VideoContentPostProcessing
from scripts.claude_cli.content_audio.post_process import PostProcessAudio
from scripts.claude_cli.asset_generator.post_process import AssetGeneratorPostProcess


PREPROCESSING_MAP = {
    AssetType.DIRECTION: VideoDirectionPreProcess,
    AssetType.VIDEO: VideoPreProcess,
    AssetType.ASSETS: AssetGeneratorPreProcess,
    AssetType.AUDIO: AudioPreProcess,
}

POSTPROCESSING_MAP = {
    AssetType.DIRECTION: VideoDirectionPostProcessing,
    AssetType.VIDEO: VideoContentPostProcessing,
    AssetType.AUDIO: PostProcessAudio,
    AssetType.ASSETS: AssetGeneratorPostProcess,
}

MAX_PARALLEL_SUBAGENTS = 50

TOOLS_MAP = {
    AssetType.DIRECTION: ["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
    AssetType.VIDEO: ["Read", "Write", "Edit", "Glob", "Bash"],
    AssetType.ASSETS: ["Read", "Write", "Glob", "Bash"],
    AssetType.AUDIO: ["Read", "Write", "Edit", "Bash"],
}

ASSET_CONFIG = {
    AssetType.DIRECTION: {
        "step_name": "direction",
        "skill_names": ["video-director"],
        "model": "claude-opus-4-6",
        "execution_type": ExecutionType.MAIN_AGENT_EXECUTION,
        "effort": "medium",
        "has_example": True,
        "subagent_name": "director_agent",
        "settings_folder": str(PROMPTS_DIR / "orchestrator" / "direction"),
        "output_folder": "Direction",
        "agent_label": "DirectorAgent",
        "oauth_token": BASIC_CLAUDE_CODE_TOKEN,
        "multi_prompt": False,
    },
    AssetType.VIDEO: {
        "step_name": "code",
        "model": "sonnet",
        "execution_type": ExecutionType.SUBAGENT_EXECUTION,
        "effort": "low",
        "has_example": False,
        "subagent_name": "code_agent",
        "settings_folder": str(PROMPTS_DIR / "orchestrator" / "code"),
        "output_folder": "Video",
        "agent_label": "CodeAgent",
        "oauth_token": CODE_CLAUDE_CODE_TOKEN,
        "multi_prompt": True,
    },
    AssetType.ASSETS: {
        "step_name": "assets",
        "skill_names": ["asset-creator"],
        "model": "claude-opus-4-6",
        "execution_type": ExecutionType.MAIN_AGENT_EXECUTION,
        "effort": "low",
        "has_example": False,
        "subagent_name": "asset_generator_agent",
        "settings_folder": str(PROMPTS_DIR / "orchestrator" / "asset"),
        "output_folder": "Assets",
        "agent_label": "AssetAgent",
        "oauth_token": BASIC_CLAUDE_CODE_TOKEN,
        "multi_prompt": False,
    },
    AssetType.AUDIO: {
        "step_name": "audio",
        "skill_names": [],
        "model": "claude-opus-4-6",
        "execution_type": ExecutionType.MAIN_AGENT_EXECUTION,
        "effort": "low",
        "has_example": False,
        "subagent_name": "audio_tags_agent",
        "settings_folder": None,
        "output_folder": "Audio",
        "agent_label": "AudioAgent",
        "oauth_token": BASIC_CLAUDE_CODE_TOKEN,
        "multi_prompt": False,
    },
}

STEP_NAME_TO_ASSET_TYPE = {
    config["step_name"]: asset_type
    for asset_type, config in ASSET_CONFIG.items()
}

ALLOWED_STEP_NAMES = list(STEP_NAME_TO_ASSET_TYPE.keys())


def get_asset_type_for_step(step_name: str) -> AssetType:
    asset_type = STEP_NAME_TO_ASSET_TYPE.get(step_name)
    if not asset_type:
        raise ValueError(f"Unknown step_name: {step_name}. Must be one of: {ALLOWED_STEP_NAMES}")
    return asset_type


def get_config(asset_type: AssetType) -> dict:
    return ASSET_CONFIG.get(asset_type, {})


def get_step_name(asset_type: AssetType) -> str:
    return ASSET_CONFIG.get(asset_type, {}).get("step_name")


def get_skill_names(asset_type: AssetType) -> list:
    return ASSET_CONFIG.get(asset_type, {}).get("skill_names", [])


def get_model(asset_type: AssetType) -> str:
    return ASSET_CONFIG.get(asset_type, {}).get("model", "sonnet")


def has_example(asset_type: AssetType) -> bool:
    return ASSET_CONFIG.get(asset_type, {}).get("has_example", False)


def get_preprocessing_class(asset_type: AssetType):
    return PREPROCESSING_MAP.get(asset_type)


def get_postprocessing_class(asset_type: AssetType):
    return POSTPROCESSING_MAP.get(asset_type)


def get_tools(asset_type: AssetType) -> list:
    return TOOLS_MAP.get(asset_type, ["Read", "Edit"])


def get_effort(asset_type: AssetType) -> str:
    return ASSET_CONFIG.get(asset_type, {}).get("effort", "high")


def get_execution_type(asset_type: AssetType) -> ExecutionType:
    return ASSET_CONFIG.get(asset_type, {}).get("execution_type", ExecutionType.SUBAGENT_EXECUTION)


def get_disallowed_tools(asset_type: AssetType) -> list:
    return []
