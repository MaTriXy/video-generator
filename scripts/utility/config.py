import os
from dotenv import load_dotenv

load_dotenv()

# These must come from .env as they're needed to fetch the API config
OUTSCAL_API_KEY = os.getenv("OUTSCAL_API_KEY")
CONFIG_BASE_URL = os.getenv("CONFIG_BASE_URL", "https://production2-api-v2.outscal.com/")

# Config state (updated by load_config in app_config.py)
_api_config = {}
_config_loaded = False

def _get_config(key: str, default=None):
    return os.getenv(key, default) or _api_config.get(key)

# Static config values
PROMPT_TAG = "production"
MANIFEST_FILE = "Outputs/{topic}/manifest.json"
WEBSITE_URL = "https://outscal.com"

ELEVENLABS_API_KEY = _get_config("ELEVENLABS_API_KEY")

# ElevenLabs constant configuration values
ELEVENLABS_VOICE_ID = "mI8xLTBNjMXAf31I4xlB"
ELEVENLABS_PRIMARY_MODEL = "eleven_v3"
ELEVENLABS_FALLBACK_MODEL = "eleven_multilingual_v2"
ELEVENLABS_SPEED = "1.1"
ELEVENLABS_STABILITY = "1.0"
ELEVENLABS_SIMILARITY = "0.65"
ELEVEN_LABS_DICTIONARY = "8fhkpKwIYubK6X8g1AMy"

# Langfuse
LANGFUSE_PUBLIC_KEY = _get_config("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = _get_config("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = _get_config("LANGFUSE_HOST", "https://langfuse.outscal.com")

AWS_ACCESS_KEY_ID = _get_config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = _get_config("AWS_SECRET_ACCESS_KEY")
AWS_REGION = _get_config("AWS_REGION", "ap-south-1")

# Payload CMS API
PAYLOAD_API_BASE_URL = _get_config("PAYLOAD_API_BASE_URL", "https://admin-v2.outscal.com")
PAYLOAD_AUTH_TOKEN = _get_config("PAYLOAD_AUTH_TOKEN")

DIRECTION_PROMPT_TAG = _get_config("DIRECTION_PROMPT_TAG", PROMPT_TAG)
ASSETS_PROMPT_TAG = _get_config("ASSETS_PROMPT_TAG", PROMPT_TAG)
DESIGN_PROMPT_TAG = _get_config("DESIGN_PROMPT_TAG", PROMPT_TAG)
VIDEO_PROMPT_TAG = _get_config("VIDEO_PROMPT_TAG", PROMPT_TAG)

# Load config from API on module import
from scripts.controllers.config.app_config import load_config
load_config()