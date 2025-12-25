import sys
from pathlib import Path

from scripts.logging_config import get_utility_logger,set_console_logging
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import requests
from typing import Dict, Any

logger = get_utility_logger(__name__)
set_console_logging(False)

def load_config() -> Dict[str, Any]:
    """Load configuration from the API. Call this and wait before using config values."""
    import scripts.utility.config as cfg

    if cfg._config_loaded:
        return cfg._api_config

    if not cfg.OUTSCAL_API_KEY:
        logger.warning("OUTSCAL_API_KEY not set, falling back to .env values")
        cfg._config_loaded = True
        return {}

    api_endpoint = f"{cfg.CONFIG_BASE_URL.rstrip('/')}/api/video-api/credentials"

    response = requests.post(
        api_endpoint,
        headers={
            "Content-Type": "application/json"
        },
        json={"apiKey": cfg.OUTSCAL_API_KEY}
    )

    data = response.json()

    if data.get("errors") and len(data["errors"]) > 0:
        logger.error(f"API Error: {data['errors'][0].get('message', 'Unknown error')}")
        cfg._config_loaded = True
        return {}

    cfg._api_config = data
    cfg._config_loaded = True
    logger.info(f"Fetched config from API: {cfg._api_config}")

    # Update module-level variables with API config
    cfg.ELEVENLABS_API_KEY = cfg._get_config("ELEVENLABS_API_KEY")
    cfg.LANGFUSE_PUBLIC_KEY = cfg._get_config("LANGFUSE_PUBLIC_KEY")
    cfg.LANGFUSE_SECRET_KEY = cfg._get_config("LANGFUSE_SECRET_KEY")
    cfg.LANGFUSE_HOST = cfg._get_config("LANGFUSE_HOST", "https://langfuse.outscal.com")
    cfg.AWS_ACCESS_KEY_ID = cfg._get_config("AWS_ACCESS_KEY_ID")
    cfg.AWS_SECRET_ACCESS_KEY = cfg._get_config("AWS_SECRET_ACCESS_KEY")
    cfg.AWS_REGION = cfg._get_config("AWS_REGION", "ap-south-1")
    cfg.PAYLOAD_API_BASE_URL = cfg._get_config("PAYLOAD_API_BASE_URL", "https://admin-v2.outscal.com")
    cfg.PAYLOAD_AUTH_TOKEN = cfg._get_config("PAYLOAD_AUTH_TOKEN")
    cfg.DIRECTION_PROMPT_TAG = cfg._get_config("DIRECTION_PROMPT_TAG", cfg.PROMPT_TAG)
    cfg.ASSETS_PROMPT_TAG = cfg._get_config("ASSETS_PROMPT_TAG", cfg.PROMPT_TAG)
    cfg.DESIGN_PROMPT_TAG = cfg._get_config("DESIGN_PROMPT_TAG", cfg.PROMPT_TAG)
    cfg.VIDEO_PROMPT_TAG = cfg._get_config("VIDEO_PROMPT_TAG", cfg.PROMPT_TAG)

    return cfg._api_config

if __name__ == "__main__":
    config = load_config()
    print(config)