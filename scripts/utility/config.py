import os
from dotenv import load_dotenv
load_dotenv()


# Langfuse
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

WEBSITE_URL="https://outscal.com"

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# Payload CMS API
PAYLOAD_API_BASE_URL = os.getenv("PAYLOAD_API_BASE_URL")
PAYLOAD_AUTH_TOKEN = os.getenv("PAYLOAD_AUTH_TOKEN")

PAYLOAD_CONFIG_BASE_URL = os.getenv("PAYLOAD_CONFIG_BASE_URL")
PAYLOAD_CONFIG_API_KEY = os.getenv("PAYLOAD_CONFIG_API_KEY")
PAYLOAD_CONFIG_ID = os.getenv("PAYLOAD_CONFIG_ID")
# LLM Provider API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ElevenLabs for Audio Generation
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Google Cloud Text-to-Speech for Audio Generation
GOOGLE_CLOUD_TTS_API_KEY = os.getenv("GOOGLE_CLOUD_TTS_API_KEY")

# Discord for Notifications
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Web Search Agent Configuration
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "true").lower() == "true"
WEB_SEARCH_MODEL = os.getenv("WEB_SEARCH_MODEL", "gemini-2.0-flash-exp")
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "10"))

# Prompt Tags Configuration
# Default tag used when specific asset tag is not defined
PROMPT_TAG = "production"
MANIFEST_FILE="Outputs/{topic}/manifest.json"

# Asset-specific prompt tags (fallback to PROMPT_TAG if not set)
RESEARCH_PROMPT_TAG = os.getenv("RESEARCH_PROMPT_TAG", PROMPT_TAG)
SCRIPT_PROMPT_TAG = os.getenv("SCRIPT_PROMPT_TAG", PROMPT_TAG)
TRANSCRIPT_PROMPT_TAG = os.getenv("TRANSCRIPT_PROMPT_TAG", PROMPT_TAG)
AUDIO_PROMPT_TAG = os.getenv("AUDIO_PROMPT_TAG", PROMPT_TAG)
DIRECTION_PROMPT_TAG = os.getenv("DIRECTION_PROMPT_TAG", PROMPT_TAG)
ASSETS_PROMPT_TAG = os.getenv("ASSETS_PROMPT_TAG", PROMPT_TAG)
DESIGN_PROMPT_TAG = os.getenv("DESIGN_PROMPT_TAG", PROMPT_TAG)
VIDEO_PROMPT_TAG = os.getenv("VIDEO_PROMPT_TAG", PROMPT_TAG)