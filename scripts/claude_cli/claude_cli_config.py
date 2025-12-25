import os
from scripts.enums import AssetType
from scripts.utility.config import (
    DIRECTION_PROMPT_TAG,
    ASSETS_PROMPT_TAG,
    DESIGN_PROMPT_TAG,
    VIDEO_PROMPT_TAG,
)

class ClaudeCliConfig:

    TOPIC = None
    BASE_OUTPUT_PATH = "Outputs"
    METADATA_PATH = "Outputs/{topic}/{type}/v{version}/metadata_log.json"
    VIDEO_URL_PATH = "Outputs/video_url.json"
    STYLE_MAPPING = {
        "Cartoon": "kurzgesagt",
        "Pencil": "what-if",
        "Infographic": "infographicshow",
        "Neon": "4g5g"
    }
    FONT_URLS = {
        STYLE_MAPPING["Pencil"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Pencil.otf", "format": "opentype"},
        STYLE_MAPPING["Infographic"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Infographic.TTF", "format": "truetype"},
        STYLE_MAPPING["Neon"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Neon.TTF", "format": "truetype"},
    }
    ASSET_PATHS = {
        AssetType.RESEARCH: {
            "latest_file": "Outputs/{topic}/Research/latest.json",
        },
        AssetType.SCRIPT: {
            "latest_file": "Outputs/{topic}/Scripts/latest.json",
            "final_path": "Outputs/{topic}/Scripts/script-v1.md",
            "variant_path": "Outputs/{topic}/Scripts/script-v1-with-emotions.md",
        },
        AssetType.TRANSCRIPT: {
            "latest_file": "Outputs/{topic}/Transcript/latest.json",
        },
        AssetType.AUDIO: {
            "latest_file": "Outputs/{topic}/Audio/latest.mp3",
        },
        AssetType.DIRECTION: {
            "prompt_file": "Outputs/{topic}/Direction/Prompts/prompt.md",
            "latest_file": "Outputs/{topic}/Direction/Latest/latest.json",
            "prompt_name": "Course-Creation/Video/Director/Direction-Creation-Prompt-Modular",
            "prompt_tag": DIRECTION_PROMPT_TAG,
        },
        AssetType.ASSETS: {
            "prompt_file": "Outputs/{topic}/Assets/Prompts/prompt.md",
            "latest_file": "Outputs/{topic}/Assets/Latest/latest_{{asset_name}}.svg",
            "prompt_name": "Course-Creation/Video/Assets/Asset-Generation-Prompt-Modular",
            "metadata_file": "Outputs/{topic}/Assets/metadata.json",
            "prompt_tag": ASSETS_PROMPT_TAG,
        },
        AssetType.DESIGN: {
            "prompt_file": "Outputs/{topic}/Design/Prompts/prompt_{{scene_index}}.md",
            "latest_file": "Outputs/{topic}/Design/Latest/latest_{{scene_index}}.json",
            "prompt_name": "Course-Creation/Video/Designer/Designer-Creation-Prompt-Modular",
            "metadata_file": "Outputs/{topic}/Design/metadata.json",
            "prompt_tag": DESIGN_PROMPT_TAG,
        },
        AssetType.VIDEO: {
            "prompt_file": "Outputs/{topic}/Video/Prompts/prompt_{{scene_index}}.md",
            "latest_file": "Outputs/{topic}/Video/Latest/scene_{{scene_index}}.tsx",
            "metadata_file": "Outputs/{topic}/Video/metadata.json",
            "prompt_name": "Course-Creation/Video/Scene/Scene-Creation-Prompt-Modular",
            "prompt_tag": VIDEO_PROMPT_TAG,
        }
    }

    @classmethod
    def get_prompt_path(cls, asset_type: AssetType) -> str:
        return cls.ASSET_PATHS[asset_type]["prompt_file"].format(topic=cls.TOPIC)

    @classmethod
    def get_prompt_name(cls, asset_type: AssetType) -> str:
        return cls.ASSET_PATHS[asset_type]["prompt_name"].format(topic=cls.TOPIC)

    @classmethod
    def get_gen_metadata_path(cls, asset_type: AssetType, version: int) -> str:
        return cls.METADATA_PATH.format(type=asset_type.value, version=version,topic=cls.TOPIC)

    @classmethod
    def get_metadata_path(cls, asset_type: AssetType) -> str:
        return cls.ASSET_PATHS[asset_type]["metadata_file"].format(topic=cls.TOPIC)

    @classmethod
    def get_latest_path(cls, asset_type: AssetType) -> str:
        return cls.ASSET_PATHS[asset_type]["latest_file"].format(topic=cls.TOPIC)

    @classmethod
    def get_final_path(cls, asset_type: AssetType) -> str:
        return cls.ASSET_PATHS[asset_type]["final_path"].format(topic=cls.TOPIC)

    @classmethod
    def get_variant_path(cls, asset_type: AssetType) -> str:
        return cls.ASSET_PATHS[asset_type]["variant_path"].format(topic=cls.TOPIC)

    @classmethod
    def get_prompt_tag(cls, asset_type: AssetType) -> str:
        return cls.ASSET_PATHS[asset_type].get("prompt_tag", "production").format(topic=cls.TOPIC)

    @classmethod
    def set_topic(cls, topic: str) -> None:
        cls.TOPIC = topic