"""
Batched audio generation utilities for handling scripts longer than ElevenLabs' 5000 character limit.

This module provides:
1. Text chunking - splits text at sentence boundaries while respecting character limits
2. MP3 merging - combines multiple MP3 files using pydub
3. Transcript merging - merges word-level transcripts with proper timestamp offsets
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from pydub import AudioSegment

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('audio_batch_processor')

ELEVENLABS_CHAR_LIMIT = 5000
SAFETY_MARGIN = 200  # Leave some buffer below the limit


def split_text_into_chunks(text: str, max_chars: int = ELEVENLABS_CHAR_LIMIT - SAFETY_MARGIN) -> List[str]:
    """
    Split text into chunks at sentence boundaries, each chunk under max_chars.

    Args:
        text: The full script text to split
        max_chars: Maximum characters per chunk (default: 4900)

    Returns:
        List of text chunks, each under max_chars
    """
    if len(text) <= max_chars:
        logger.info(f"Text is {len(text)} chars, no chunking needed")
        return [text]

    # Split by sentence-ending punctuation, keeping the punctuation
    sentence_pattern = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_pattern, text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If single sentence exceeds limit, split by clauses or words
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # Try splitting by commas/semicolons first
            clause_chunks = _split_long_sentence(sentence, max_chars)
            chunks.extend(clause_chunks)
            continue

        # Check if adding this sentence would exceed limit
        potential_chunk = current_chunk + (" " if current_chunk else "") + sentence

        if len(potential_chunk) <= max_chars:
            current_chunk = potential_chunk
        else:
            # Save current chunk and start new one
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    logger.info(f"Split {len(text)} chars into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        logger.debug(f"Chunk {i+1}: {len(chunk)} chars")

    return chunks


def _split_long_sentence(sentence: str, max_chars: int) -> List[str]:
    """
    Split a sentence that exceeds max_chars by clauses or words.
    """
    # Try splitting by commas, semicolons, or colons
    clause_pattern = r'(?<=[,;:])\s+'
    clauses = re.split(clause_pattern, sentence)

    if len(clauses) > 1:
        chunks = []
        current_chunk = ""

        for clause in clauses:
            potential = current_chunk + (" " if current_chunk else "") + clause
            if len(potential) <= max_chars:
                current_chunk = potential
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(clause) > max_chars:
                    # Still too long, split by words
                    chunks.extend(_split_by_words(clause, max_chars))
                    current_chunk = ""
                else:
                    current_chunk = clause

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    # No clauses, split by words
    return _split_by_words(sentence, max_chars)


def _split_by_words(text: str, max_chars: int) -> List[str]:
    """
    Split text by words when sentence/clause splitting isn't possible.
    """
    words = text.split()
    chunks = []
    current_chunk = ""

    for word in words:
        potential = current_chunk + (" " if current_chunk else "") + word
        if len(potential) <= max_chars:
            current_chunk = potential
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = word

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def merge_mp3_files(mp3_paths: List[str], output_path: str) -> bool:
    """
    Merge multiple MP3 files into a single file using pydub.

    Args:
        mp3_paths: List of paths to MP3 files to merge (in order)
        output_path: Path for the merged output file

    Returns:
        True if successful, False otherwise
    """
    if not mp3_paths:
        logger.error("No MP3 files provided for merging")
        return False

    if len(mp3_paths) == 1:
        # Just copy the single file
        import shutil
        shutil.copy(mp3_paths[0], output_path)
        logger.info(f"Single MP3 file copied to {output_path}")
        return True

    try:
        logger.info(f"Merging {len(mp3_paths)} MP3 files...")

        # Load and concatenate all audio files
        combined = AudioSegment.empty()

        for i, mp3_path in enumerate(mp3_paths):
            logger.debug(f"Loading part {i+1}: {mp3_path}")
            audio_segment = AudioSegment.from_mp3(mp3_path)
            combined += audio_segment
            logger.debug(f"Part {i+1} duration: {len(audio_segment)}ms")

        # Export merged audio
        combined.export(output_path, format="mp3")

        logger.info(f"Merged audio saved to {output_path} (total duration: {len(combined)}ms)")
        return True

    except Exception as e:
        logger.error(f"Error merging MP3 files: {e}")
        return False


def get_mp3_duration_ms(mp3_path: str) -> int:
    """
    Get the duration of an MP3 file in milliseconds.

    Args:
        mp3_path: Path to the MP3 file

    Returns:
        Duration in milliseconds
    """
    try:
        audio = AudioSegment.from_mp3(mp3_path)
        return len(audio)
    except Exception as e:
        logger.error(f"Error getting MP3 duration: {e}")
        return 0


def merge_transcripts(transcript_paths: List[str], audio_paths: List[str], output_path: str) -> Tuple[bool, List[Dict]]:
    """
    Merge multiple word-level transcripts with proper timestamp offsets.

    Each subsequent transcript's timestamps are offset by the cumulative
    duration of all previous audio files.

    Args:
        transcript_paths: List of paths to transcript JSON files (in order)
        audio_paths: List of paths to corresponding MP3 files (for duration calculation)
        output_path: Path for the merged transcript output

    Returns:
        Tuple of (success: bool, merged_words: List[Dict])
    """
    if len(transcript_paths) != len(audio_paths):
        logger.error("Transcript and audio path counts must match")
        return False, []

    if not transcript_paths:
        logger.error("No transcripts provided for merging")
        return False, []

    try:
        merged_words = []
        cumulative_offset_ms = 0

        for i, (transcript_path, audio_path) in enumerate(zip(transcript_paths, audio_paths)):
            logger.debug(f"Processing transcript {i+1}: {transcript_path}")

            # Load transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                words = json.load(f)

            # Apply offset to all timestamps
            for word_data in words:
                merged_words.append({
                    "word": word_data["word"],
                    "start_ms": word_data["start_ms"] + cumulative_offset_ms,
                    "end_ms": word_data["end_ms"] + cumulative_offset_ms
                })

            # Get duration of this audio file for next offset
            audio_duration = get_mp3_duration_ms(audio_path)
            cumulative_offset_ms += audio_duration

            logger.debug(f"Part {i+1}: {len(words)} words, audio duration: {audio_duration}ms, new offset: {cumulative_offset_ms}ms")

        # Save merged transcript
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_words, f, indent=2, ensure_ascii=False)

        logger.info(f"Merged transcript saved to {output_path} ({len(merged_words)} words)")
        return True, merged_words

    except Exception as e:
        logger.error(f"Error merging transcripts: {e}")
        return False, []


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Remove temporary chunk files after successful merge.

    Args:
        file_paths: List of file paths to delete
    """
    for path in file_paths:
        try:
            Path(path).unlink(missing_ok=True)
            logger.debug(f"Deleted temp file: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete temp file {path}: {e}")
