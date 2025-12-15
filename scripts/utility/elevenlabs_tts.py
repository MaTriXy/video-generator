"""
ElevenLabs Text-to-Speech service implementation.
Generates audio with word-level timestamps using character alignment data.
"""

import json
import base64
import requests
from typing import Dict, List, Tuple, Optional
from scripts.utility.config import ELEVENLABS_API_KEY
from scripts.logging_config import get_utility_logger

logger = get_utility_logger('elevenlabs_tts')

# Validation thresholds
CONSECUTIVE_IDENTICAL_THRESHOLD = 5  # Max consecutive non-punctuation words with same timestamp


class ElevenLabsTimingError(Exception):
    pass


def _validate_transcript_timing(words: List[Dict]) -> Tuple[bool, Optional[str]]:
    if not words:
        return False, "Empty transcript"

    punct = set([".", ",", ";", ":", "!", "?", "(", ")", "[", "]", "{", "}", "'", "\"", "—", "–", "-"])

    # Check for consecutive words with identical timestamps
    consecutive_identical = 0
    last_timestamp = None
    problematic_sections = []
    section_start_idx = 0

    for i, word_data in enumerate(words):
        word = word_data.get("word", "")
        start_ms = word_data.get("start_ms")
        end_ms = word_data.get("end_ms")

        # Skip punctuation for consecutive check
        if word in punct or len(word) <= 1:
            continue

        # Check for identical timestamps (start == end for the same timestamp value)
        current_timestamp = (start_ms, end_ms)

        if last_timestamp is not None and current_timestamp == last_timestamp and start_ms == end_ms:
            consecutive_identical += 1
            if consecutive_identical >= CONSECUTIVE_IDENTICAL_THRESHOLD:
                # Find the range of affected words
                section_end_idx = i
                affected_words = [words[j]["word"] for j in range(section_start_idx, min(section_end_idx + 1, len(words)))]
                problematic_sections.append({
                    "start_idx": section_start_idx,
                    "end_idx": section_end_idx,
                    "timestamp_ms": start_ms,
                    "word_count": consecutive_identical + 1,
                    "sample_words": affected_words[:5]  # First 5 words as sample
                })
        else:
            consecutive_identical = 0
            section_start_idx = i

        last_timestamp = current_timestamp

    if problematic_sections:
        total_affected = sum(s["word_count"] for s in problematic_sections)
        error_msg = (
            f"ElevenLabs timing data corrupted: {len(problematic_sections)} section(s) with identical timestamps. "
            f"Total {total_affected} words affected. "
            f"First problematic section at {problematic_sections[0]['timestamp_ms']}ms: "
            f"words {problematic_sections[0]['sample_words']}"
        )
        return False, error_msg

    return True, None

def _fetch_audio_and_timestamps(text: str, api_key: str, config: Dict, phonetics_dict_id: str):
    try:
        """Calls the ElevenLabs API to get audio and timestamp data."""
        voice_id = config.get("voice_id", "QzyAJCjnDHxLPazR6j3v")  # Default voice
        model_id = config.get("model_id", "eleven_multilingual_v2")
        speed = config.get("speed", 1.1)
        stability = config.get("stability", 0.8)
        similarity = config.get("similarity", 0.65)
        logger.info(f"Fetching audio and timestamps with phonetics dictionary ID: {phonetics_dict_id}")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {"speed": speed, "stability": stability, "similarity": similarity},
            "pronunciation_dictionary_locators": [{
                "pronunciation_dictionary_id":phonetics_dict_id
            }]
        }
        logger.debug(f"Sending payload to ElevenLabs: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching audio and timestamps: {e}")
        return None
        raise

def _create_word_transcript(alignment_data: Dict, transcript_path: str) -> List[Dict]:
    chars = alignment_data["characters"]
    starts = alignment_data["character_start_times_seconds"]
    ends = alignment_data["character_end_times_seconds"]

    words, word, w_start = [], "", None
    # Correctly defined set of punctuation
    punct = set([".", ",", ";", ":", "!", "?", "(", ")", "[", "]", "{", "}", "'", "\"", "—", "–", "-"])
    prev_end = 0

    for ch, st, en in zip(chars, starts, ends):
        if ch.isspace() or ch == "\n":
            if word:
                words.append({"word": word, "start_ms": int(w_start * 1000), "end_ms": int(prev_end * 1000)})
                word, w_start = "", None
            continue

        if ch in punct:
            if word:
                words.append({"word": word, "start_ms": int(w_start * 1000), "end_ms": int(prev_end * 1000)})
                word, w_start = "", None
            words.append({"word": ch, "start_ms": int(st * 1000), "end_ms": int(en * 1000)})
            prev_end = en
            continue

        if not word:
            w_start = st
        word += ch
        prev_end = en

    if word:
        words.append({"word": word, "start_ms": int(w_start * 1000), "end_ms": int(prev_end * 1000)})

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)
    logger.info(f"Word transcript successfully saved to {transcript_path}")

    return words

def _save_audio_file(audio_base64: str, audio_path: str):
    """Saves the base64 encoded audio to a file."""
    with open(audio_path, 'wb') as f:
        f.write(base64.b64decode(audio_base64))
    logger.info(f"Audio successfully saved to {audio_path}")

def generate_audio(text: str, audio_output_path: str, transcript_output_path: str, config: Dict, phonetics_dict_id: str):
    logger.info("Generating audio with ElevenLabs...")

    # Check API key
    api_key = ELEVENLABS_API_KEY or config.get('elevenlabs', {}).get('api_key')
    if not api_key:
        logger.error("ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.")
        raise ValueError("ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.")

    el_config = config.get('elevenlabs', config)

    # Fetch audio and timestamps from ElevenLabs
    api_data = _fetch_audio_and_timestamps(text, api_key, el_config, phonetics_dict_id)

    if not api_data:
        raise Exception("ElevenLabs API returned no data")

    # Save audio file
    _save_audio_file(api_data["audio_base64"], audio_output_path)

    # Create transcript and get words for validation
    words = _create_word_transcript(api_data["alignment"], transcript_output_path)

    # Validate timing data
    is_valid, error_msg = _validate_transcript_timing(words)

    if is_valid:
        logger.info("ElevenLabs audio generation completed successfully")
        return
    else:
        raise ElevenLabsTimingError(
            f"ERROR: ElevenLabs timing data corrupted: {error_msg}\n\n"
            f"Please try:\n change eleven labs model to 2.5 instead of 3.0"
        )