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
ELEVENLABS_PRIMARY_VOICE_ID = _get_config("ELEVENLABS_PRIMARY_VOICE_ID", "mI8xLTBNjMXAf31I4xlB")
ELEVENLABS_FALLBACK_VOICE_ID = _get_config("ELEVENLABS_FALLBACK_VOICE_ID", "yl2ZDV1MzN4HbQJbMihG")
ELEVENLABS_PRIMARY_MODEL = _get_config("ELEVENLABS_PRIMARY_MODEL", "eleven_v3")
ELEVENLABS_FALLBACK_MODEL = _get_config("ELEVENLABS_FALLBACK_MODEL", "eleven_multilingual_v2")
ELEVENLABS_SPEED = _get_config("ELEVENLABS_SPEED", "1.1")
ELEVENLABS_FAST_SPEED_VOICE_ID = _get_config("ELEVENLABS_FAST_SPEED_VOICE_ID")
ELEVENLABS_FAST_SPEED = _get_config("ELEVENLABS_FAST_SPEED", "1.5")
ELEVENLABS_STABILITY = _get_config("ELEVENLABS_STABILITY", "1.0")
ELEVENLABS_SIMILARITY = _get_config("ELEVENLABS_SIMILARITY", "0.65")
ELEVEN_LABS_DICTIONARY = _get_config("ELEVEN_LABS_DICTIONARY", "")

OUTSCAL_SERVER_KEY = _get_config("OUTSCAL_SERVER_KEY", "aaaaaaaaaa")

DIRECTION_PROMPT_TAG = _get_config("DIRECTION_PROMPT_TAG", PROMPT_TAG)
ASSETS_PROMPT_TAG = _get_config("ASSETS_PROMPT_TAG", PROMPT_TAG)
VIDEO_PROMPT_TAG = _get_config("VIDEO_PROMPT_TAG", PROMPT_TAG)

BASIC_CLAUDE_CODE_TOKEN = _get_config("BASIC_CLAUDE_CODE_TOKEN")

MAPBOX_TOKENS = _get_config("MAPBOX_TOKENS", "")
ADD_EMOTIONS = os.getenv("ADD_EMOTIONS", "true").lower() == "true"

# Load config from API on module import
from scripts.controllers.config.app_config import load_config
load_config()