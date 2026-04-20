from scripts.enums import AssetType
from scripts.utility.config import (
    DIRECTION_PROMPT_TAG,
    ASSETS_PROMPT_TAG,
    VIDEO_PROMPT_TAG,
)
from scripts.path_setup import PROMPTS_DIR

class ClaudeCliConfig:

    TOPIC = None
    BASE_OUTPUT_PATH = "Outputs"
    ARTSTYLE_DIR = "Course-Creation/Video/artstyles"
    EXAMPLE_DIR_PATH = ".claude/skills/video-designer/examples"
    HOOK_GUIDELINES_PATH = ".claude/skills/video-designer/references/hook-guidelines.md"
    EXAMPLE_MAP = {
       "infographicshow": "infographic.md",
        "4g5g": "neon.md",
        "what-if": "pencil.md",
        "minimal-blue": "minimal-blue.md",
        "vox": "vox.md",
        "typography-apple": "typography-apple.md",
    }
    METADATA_PATH = "Outputs/{topic}/{type}/v{version}/metadata_log.json"
    VIDEO_URL_PATH = "Outputs/video_url.json"
    STYLE_MAPPING = {
        "Pencil": "what-if",
        "Infographic": "infographicshow",
        "Neon": "4g5g",
        "Minimal_Blue": "minimal-blue",
        "Vox": "vox",
        "Typography_Apple": "typography-apple"
    }
    FONT_URLS = {
        STYLE_MAPPING["Pencil"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Pencil.otf", "format": "opentype"},
        STYLE_MAPPING["Infographic"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Infographic.TTF", "format": "truetype"},
        STYLE_MAPPING["Neon"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Neon.TTF", "format": "truetype"},
        STYLE_MAPPING["Minimal_Blue"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Inter-VariableFont_opsz%2Cwght.ttf", "format": "truetype"},
        STYLE_MAPPING["Vox"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Inter-VariableFont_opsz%2Cwght.ttf", "format": "truetype"},
        STYLE_MAPPING["Typography_Apple"]: {"url": "https://outscal.s3.ap-south-1.amazonaws.com/assets/fonts/Inter-VariableFont_opsz%2Cwght.ttf", "format": "truetype"},
    }
    ASSET_PATHS = {
        AssetType.RESEARCH: {
            "latest_file": "Outputs/{topic}/Research/latest.json",
        },
        AssetType.SCRIPT: {
            "latest_file": "Outputs/{topic}/Scripts/script-user-input.md",
            "final_path": "Outputs/{topic}/Scripts/script.md",
            "variant_path": "Outputs/{topic}/Scripts/script-with-emotions.md",
        },
        AssetType.TRANSCRIPT: {
            "latest_file": "Outputs/{topic}/Transcript/latest.json",
        },
        AssetType.AUDIO: {
            "prompt_file": "Outputs/{topic}/Audio/Prompts/prompt.md",
            "latest_file": "Outputs/{topic}/Audio/latest.mp3",
            "prompt_name": "",
        },
        AssetType.DIRECTION: {
            "prompt_file": "Outputs/{topic}/Direction/Prompts/prompt.md",
            "latest_file": "Outputs/{topic}/Direction/Latest/latest.json",
            "prompt_name": "Course-Creation/Video/Director/Direction-Creation-Prompt-Modular",
            "prompt_tag": DIRECTION_PROMPT_TAG,
        },
        AssetType.ASSETS: {
            "prompt_file": "Outputs/{topic}/Assets/Prompts/prompt.md",
            "latest_file": "Outputs/{topic}/Assets/Latest/latest_asset.txt",
            "prompt_name": "Course-Creation/Video/Assets/Asset-Generation-Prompt-Modular",
            "metadata_file": "Outputs/{topic}/Assets/metadata.json",
            "artstyle_config": "Course-Creation/Video/Assets/asset_artstyle_config.json",
            "prompt_tag": ASSETS_PROMPT_TAG,
        },
        AssetType.VIDEO: {
            "prompt_file": "Outputs/{topic}/Video/Prompts/prompt_{{scene_index}}.md",
            "latest_file": "Outputs/{topic}/Video/Latest/scene_{{scene_index}}.tsx",
            "metadata_file": "Outputs/{topic}/Video/metadata.json",
            "prompt_name": "Course-Creation/Video/Scene/Scene-Creation-Prompt-Modular",
            "prompt_tag": VIDEO_PROMPT_TAG,
        }
    }

    def __init__(self, topic: str):
        self.topic = topic

    def get_prompt_path(self, asset_type: AssetType) -> str:
        return self.ASSET_PATHS[asset_type]["prompt_file"].format(topic=self.topic)

    def get_prompt_name(self, asset_type: AssetType) -> str:
        return self.ASSET_PATHS[asset_type]["prompt_name"].format(topic=self.topic)

    def get_gen_metadata_path(self, asset_type: AssetType, version: int) -> str:
        return self.METADATA_PATH.format(type=asset_type.value, version=version, topic=self.topic)

    def get_metadata_path(self, asset_type: AssetType) -> str:
        return self.ASSET_PATHS[asset_type]["metadata_file"].format(topic=self.topic)

    def get_latest_path(self, asset_type: AssetType) -> str:
        return self.ASSET_PATHS[asset_type]["latest_file"].format(topic=self.topic)

    def get_final_path(self, asset_type: AssetType) -> str:
        return self.ASSET_PATHS[asset_type]["final_path"].format(topic=self.topic)

    def get_variant_path(self, asset_type: AssetType) -> str:
        return self.ASSET_PATHS[asset_type]["variant_path"].format(topic=self.topic)

    def get_prompt_tag(self, asset_type: AssetType) -> str:
        return self.ASSET_PATHS[asset_type].get("prompt_tag", "production").format(topic=self.topic)
    def get_artstyle_config_path(self, asset_type: AssetType) -> str:
        return str(PROMPTS_DIR / self.ASSET_PATHS[asset_type]["artstyle_config"])

    def set_topic(self, topic: str) -> None:
        self.topic = topic
