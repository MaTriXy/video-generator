"""Generate a sound effect via ElevenLabs and save it to a local directory."""
import os
import time
import uuid
from pathlib import Path

import httpx

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('tools.generate_sound_effect_tool')

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/sound-generation"
OUTPUT_FORMAT = "mp3_44100_128"


async def generate_sound_effect(
    text: str,
    duration_seconds: float = None,
    prompt_influence: float = 0.3,
    loop: bool = False,
    model_id: str = "eleven_text_to_sound_v2",
    output_dir: str = None,
) -> dict:
    start_time = time.time()
    logger.info(f"[SOUND_EFFECT] Request: text='{text[:80]}'")

    if not text or not text.strip():
        return {"success": False, "message": "text is required and cannot be empty."}

    if duration_seconds is not None and (duration_seconds < 0.5 or duration_seconds > 30):
        return {"success": False, "message": "duration_seconds must be between 0.5 and 30."}

    if prompt_influence is not None and (prompt_influence < 0 or prompt_influence > 1):
        return {"success": False, "message": "prompt_influence must be between 0 and 1."}

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return {"success": False, "message": "ELEVENLABS_API_KEY environment variable is not set."}

    body = {
        "text": text,
        "loop": loop,
        "prompt_influence": prompt_influence,
        "model_id": model_id,
    }
    if duration_seconds is not None:
        body["duration_seconds"] = duration_seconds

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ELEVENLABS_API_URL,
                json=body,
                params={"output_format": OUTPUT_FORMAT},
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500] if e.response else "No response body"
        logger.error(f"[SOUND_EFFECT] API error {e.response.status_code}: {error_body}")
        return {"success": False, "message": f"ElevenLabs API error ({e.response.status_code}): {error_body}"}
    except Exception as e:
        logger.error(f"[SOUND_EFFECT] ElevenLabs request failed: {e}")
        return {"success": False, "message": f"Failed to generate sound effect: {e}"}

    audio_bytes = response.content
    file_size = len(audio_bytes)

    try:
        target_dir = Path(output_dir) if output_dir else Path.cwd()
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}.mp3"
        file_path = target_dir / file_name
        file_path.write_bytes(audio_bytes)
        logger.info(f"[SOUND_EFFECT] Saved to {file_path}")
    except Exception as e:
        logger.error(f"[SOUND_EFFECT] Local save failed: {e}")
        return {"success": False, "message": f"Failed to save sound effect locally: {e}"}

    elapsed = time.time() - start_time
    logger.info(f"[SOUND_EFFECT] Complete: {file_size} bytes in {elapsed*1000:.2f}ms")
    return {
        "success": True,
        "path": str(file_path),
        "filename": file_name,
        "time": round(elapsed, 2),
    }
