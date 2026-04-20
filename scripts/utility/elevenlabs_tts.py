import json
import asyncio
import base64
import aiohttp
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scripts.utility.config import ELEVENLABS_API_KEY
from scripts.logging_config import get_utility_logger
from scripts.utility.audio_batch_processor import (
    split_text_into_chunks,
    merge_mp3_files,
    merge_transcripts,
    ELEVENLABS_CHAR_LIMIT
)

logger = get_utility_logger('elevenlabs_tts')

class ElevenLabsTimingError(Exception):
    pass


def _validate_transcript_timing(words: List[Dict]) -> Tuple[bool, Optional[str], int]:
    if not words:
        return False, "Empty transcript", 0

    punct = set([".", ",", ";", ":", "!", "?", "(", ")", "[", "]", "{", "}", "'", "\"", "—", "–", "-"])

    # Skip words inside square brackets — these are v3 emotion tags (e.g. [matter-of-factly])
    # and are not spoken content. ElevenLabs often returns zero-duration timing for them.
    inside_bracket = False
    bracket_skipped = []
    filtered_words = []
    for i, word_data in enumerate(words):
        word = word_data.get("word", "")
        if word == "[":
            inside_bracket = True
            continue
        if word == "]":
            inside_bracket = False
            continue
        if inside_bracket:
            bracket_skipped.append(word)
            continue
        if word in punct or len(word) <= 1:
            continue
        filtered_words.append({
            "index": i,
            "word": word,
            "start_ms": word_data.get("start_ms"),
            "end_ms": word_data.get("end_ms")
        })

    if bracket_skipped:
        logger.info(f"Skipped {len(bracket_skipped)} emotion-tag words from timing validation: {bracket_skipped}")

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


async def _fetch_audio_and_timestamps(text: str, api_key: str, config: Dict, phonetics_dict_id: str, model_override: str = None) -> Optional[Tuple[Dict, int]]:
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
        logger.debug(f"Sending payload to ElevenLabs: {json.dumps(payload)}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_text,
                    )
                data = await response.json(content_type=None)
                return data, len(text)
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


async def generate_audio(
    text: str,
    audio_output_path: str,
    transcript_output_path: str,
    config: Dict,
    phonetics_dict_id: str,
    model_override: str = None
) -> Tuple[bool, Optional[str], int, int, int]:
    logger.info("Generating audio with ElevenLabs...")

    api_key = ELEVENLABS_API_KEY
    if not api_key:
        logger.error("ElevenLabs API key not found. Set ELEVENLABS_API_KEY environment variable.")
        return False, "ElevenLabs API key not found", 0, 0, 0

    model_id = model_override if model_override else config.get("model_id", "eleven_multilingual_v2")
    result = await _fetch_audio_and_timestamps(text, api_key, config, phonetics_dict_id, model_override)

    if not result:
        return False, "ElevenLabs API returned no data", 0, 0, 0

    api_data, char_count = result

    _save_audio_file(api_data["audio_base64"], audio_output_path)
    _save_raw_alignment(api_data["alignment"], transcript_output_path, model_id)
    words = _create_word_transcript(api_data["alignment"], transcript_output_path)
    total_words = len(words)

    is_valid, error_msg, affected_count = _validate_transcript_timing(words)

    if is_valid:
        logger.info(f"ElevenLabs audio generation completed successfully (char count: {char_count})")
        return True, None, 0, total_words, char_count
    else:
        logger.warning(f"Timing validation failed: {error_msg}")
        return False, error_msg, affected_count, total_words, char_count


async def generate_audio_batched(
    text: str,
    audio_output_path: str,
    transcript_output_path: str,
    config: Dict,
    phonetics_dict_id: str,
    model_override: str = None
) -> Tuple[bool, Optional[str], int, int, int]:
    """
    Generate audio with automatic batching for scripts exceeding ElevenLabs' character limit.

    Splits long scripts into chunks, generates audio for each chunk concurrently,
    then merges all MP3s and transcripts together.

    All chunks must succeed before merging. No fallback model is used.

    Args:
        text: Full script text (any length)
        audio_output_path: Path for final merged audio
        transcript_output_path: Path for final merged transcript
        config: ElevenLabs configuration dict
        phonetics_dict_id: Pronunciation dictionary ID
        model_override: Optional model override (uses v3 by default)

    Returns:
        Tuple of (success, error_msg, affected_count, total_words, char_count)
    """
    # Check if batching is needed
    if len(text) <= ELEVENLABS_CHAR_LIMIT:
        logger.info(f"Text is {len(text)} chars, using single API call")
        return await generate_audio(
            text, audio_output_path, transcript_output_path,
            config, phonetics_dict_id, model_override
        )

    logger.info(f"Text is {len(text)} chars, batching required (limit: {ELEVENLABS_CHAR_LIMIT})")

    # Split text into chunks
    chunks = split_text_into_chunks(text)
    num_chunks = len(chunks)
    logger.info(f"Split into {num_chunks} chunks")

    # Prepare temp file paths
    audio_base = Path(audio_output_path)
    transcript_base = Path(transcript_output_path)

    temp_audio_paths = []
    temp_transcript_paths = []

    for i in range(num_chunks):
        temp_audio_paths.append(str(audio_base.parent / f"{audio_base.stem}_part{i+1}{audio_base.suffix}"))
        temp_transcript_paths.append(str(transcript_base.parent / f"{transcript_base.stem}_part{i+1}{transcript_base.suffix}"))

    # Generate audio for each chunk in parallel - all must succeed
    api_key = ELEVENLABS_API_KEY
    if not api_key:
        logger.error("ElevenLabs API key not found")
        return False, "ElevenLabs API key not found", 0, 0

    model_id = model_override if model_override else config.get("model_id", "eleven_multilingual_v2")

    async def _process_chunk(i, chunk):
        logger.info(f"Generating chunk {i+1}/{num_chunks} ({len(chunk)} chars)...")
        print(f"[Generating audio part {i+1}/{num_chunks}...]")

        result = await _fetch_audio_and_timestamps(chunk, api_key, config, phonetics_dict_id, model_override)

        if not result:
            error_msg = f"Chunk {i+1}/{num_chunks} failed: ElevenLabs API returned no data"
            logger.error(error_msg)
            return False, error_msg, 0, 0, 0

        api_data, chunk_char_count = result

        _save_audio_file(api_data["audio_base64"], temp_audio_paths[i])
        _save_raw_alignment(api_data["alignment"], temp_transcript_paths[i], model_id)
        words = _create_word_transcript(api_data["alignment"], temp_transcript_paths[i])

        is_valid, error_msg, affected_count = _validate_transcript_timing(words)
        if not is_valid:
            logger.error(f"Chunk {i+1}/{num_chunks} timing validation failed: {error_msg}")
            return False, f"Chunk {i+1} failed: {error_msg}", affected_count, len(words), chunk_char_count

        logger.info(f"Chunk {i+1}/{num_chunks} completed successfully (char count: {chunk_char_count})")
        return True, None, 0, len(words), chunk_char_count

    # Run all chunks concurrently — TaskGroup cancels siblings on first exception
    results: list = [None] * num_chunks
    chunk_failed = False
    try:
        async with asyncio.TaskGroup() as tg:
            async def _run_chunk(idx, chunk):
                result = await _process_chunk(idx, chunk)
                if not result[0]:  # success == False
                    raise RuntimeError(f"chunk_{idx}")
                results[idx] = result

            for i, chunk in enumerate(chunks):
                tg.create_task(_run_chunk(i, chunk))
    except* RuntimeError:
        chunk_failed = True

    if chunk_failed:
        for i, r in enumerate(results):
            if r is not None and not r[0]:
                return False, r[1], r[2], r[3], r[4]
        return False, "Audio chunk generation failed", 0, 0, 0

    total_char_count = 0
    for i, (success, error_msg, affected_count, word_count, chunk_char_count) in enumerate(results):
        if not success:
            return False, error_msg, affected_count, word_count, chunk_char_count
        total_char_count += chunk_char_count

    # All chunks succeeded - merge them
    logger.info("All chunks generated successfully, merging...")
    print("[Merging audio parts...]")

    # Merge MP3 files
    if not merge_mp3_files(temp_audio_paths, audio_output_path):
        return False, "Failed to merge MP3 files", 0, 0, total_char_count

    # Merge transcripts
    success, merged_words = merge_transcripts(temp_transcript_paths, temp_audio_paths, transcript_output_path)
    if not success:
        return False, "Failed to merge transcripts", 0, 0, total_char_count

    total_words = len(merged_words)

    # Validate final merged transcript
    is_valid, error_msg, affected_count = _validate_transcript_timing(merged_words)
    if not is_valid:
        logger.warning(f"Merged transcript validation failed: {error_msg}")
        return False, error_msg, affected_count, total_words, total_char_count

    logger.info(f"Batched audio generation completed: {num_chunks} chunks merged, {total_words} words, {total_char_count} chars")
    print(f"[OK] Audio generated successfully ({num_chunks} parts merged, {total_char_count} chars)")

    return True, None, 0, total_words, total_char_count
