import json
import base64
import requests
from typing import Dict, List, Tuple, Optional
from scripts.utility.config import ELEVENLABS_API_KEY
from scripts.logging_config import get_utility_logger

logger = get_utility_logger('elevenlabs_tts')

class ElevenLabsTimingError(Exception):
    pass


def _validate_transcript_timing(words: List[Dict]) -> Tuple[bool, Optional[str], int]:
    if not words:
        return False, "Empty transcript", 0

    punct = set([".", ",", ";", ":", "!", "?", "(", ")", "[", "]", "{", "}", "'", "\"", "—", "–", "-"])

    filtered_words = []
    for i, word_data in enumerate(words):
        word = word_data.get("word", "")
        if word in punct or len(word) <= 1:
            continue
        filtered_words.append({
            "index": i,
            "word": word,
            "start_ms": word_data.get("start_ms"),
            "end_ms": word_data.get("end_ms")
        })

    if not filtered_words:
        return True, None, 0

    zero_duration_words = [w for w in filtered_words if w["start_ms"] == w["end_ms"]]
    if zero_duration_words:
        affected_count = len(zero_duration_words)
        sample_words = [w["word"] for w in zero_duration_words[:5]]
        error_msg = f"ElevenLabs timing data corrupted: {affected_count} word(s) with zero duration. Sample words: {sample_words}"
        return False, error_msg, affected_count

    for i in range(1, len(filtered_words)):
        curr = filtered_words[i]
        prev = filtered_words[i - 1]

        if curr["start_ms"] == prev["start_ms"]:
            error_msg = f"ElevenLabs timing data corrupted: words '{prev['word']}' and '{curr['word']}' both start at {curr['start_ms']}ms"
            return False, error_msg, 2

        if curr["end_ms"] == prev["end_ms"]:
            error_msg = f"ElevenLabs timing data corrupted: words '{prev['word']}' and '{curr['word']}' both end at {curr['end_ms']}ms"
            return False, error_msg, 2

        if curr["start_ms"] < prev["end_ms"]:
            error_msg = f"ElevenLabs timing data corrupted: '{curr['word']}' starts at {curr['start_ms']}ms but '{prev['word']}' ends at {prev['end_ms']}ms"
            return False, error_msg, 2

        if curr["end_ms"] < prev["end_ms"]:
            error_msg = f"ElevenLabs timing data corrupted: '{curr['word']}' ends at {curr['end_ms']}ms but '{prev['word']}' ends at {prev['end_ms']}ms"
            return False, error_msg, 2

    return True, None, 0


def _fetch_audio_and_timestamps(text: str, api_key: str, config: Dict, phonetics_dict_id: str, model_override: str = None):
    try:
        voice_id = config.get("voice_id", "QzyAJCjnDHxLPazR6j3v")
        model_id = model_override if model_override else config.get("model_id", "eleven_multilingual_v2")
        speed = config.get("speed", 1.1)
        stability = config.get("stability", 1.0)
        similarity = config.get("similarity", 0.65)

        logger.info(f"Fetching audio with model: {model_id}")
        logger.info(f"Phonetics dictionary ID: {phonetics_dict_id}")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {"speed": speed, "stability": stability, "similarity_boost": similarity},
            "pronunciation_dictionary_locators": [{"pronunciation_dictionary_id": phonetics_dict_id}]
        }
        logger.debug(f"Sending payload to ElevenLabs: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching audio and timestamps: {e}")
        return None


def _create_word_transcript(alignment_data: Dict, transcript_path: str) -> List[Dict]:
    chars = alignment_data["characters"]
    starts = alignment_data["character_start_times_seconds"]
    ends = alignment_data["character_end_times_seconds"]

    words, word, w_start = [], "", None
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
    with open(audio_path, 'wb') as f:
        f.write(base64.b64decode(audio_base64))
    logger.info(f"Audio successfully saved to {audio_path}")


def validate_transcript_file(transcript_path: str) -> Tuple[bool, Optional[str], int, int]:
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            words = json.load(f)

        total_words = len(words)
        is_valid, error_msg, affected_count = _validate_transcript_timing(words)

        if is_valid:
            logger.info(f"Transcript validation passed: {transcript_path}")
            return True, None, 0, total_words
        else:
            logger.warning(f"Transcript validation failed: {error_msg}")
            return False, error_msg, affected_count, total_words

    except Exception as e:
        logger.error(f"Error validating transcript: {e}")
        return False, str(e), 0, 0


def _save_raw_alignment(alignment_data: Dict, transcript_path: str, model_id: str):
    """Save raw character-level alignment data from ElevenLabs before processing."""
    raw_path = transcript_path.replace(".json", f"_raw_{model_id}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(alignment_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Raw character alignment saved to {raw_path}")


def generate_audio(
    text: str,
    audio_output_path: str,
    transcript_output_path: str,
    config: Dict,
    phonetics_dict_id: str,
    model_override: str = None
) -> Tuple[bool, Optional[str], int, int]:
    logger.info("Generating audio with ElevenLabs...")

    api_key = ELEVENLABS_API_KEY
    if not api_key:
        logger.error("ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.")
        return False, "ElevenLabs API key not found", 0, 0

    model_id = model_override if model_override else config.get("model_id", "eleven_multilingual_v2")
    api_data = _fetch_audio_and_timestamps(text, api_key, config, phonetics_dict_id, model_override)

    if not api_data:
        return False, "ElevenLabs API returned no data", 0, 0

    _save_audio_file(api_data["audio_base64"], audio_output_path)
    _save_raw_alignment(api_data["alignment"], transcript_output_path, model_id)
    words = _create_word_transcript(api_data["alignment"], transcript_output_path)
    total_words = len(words)

    is_valid, error_msg, affected_count = _validate_transcript_timing(words)

    if is_valid:
        logger.info("ElevenLabs audio generation completed successfully")
        return True, None, 0, total_words
    else:
        logger.warning(f"Timing validation failed: {error_msg}")
        return False, error_msg, affected_count, total_words
