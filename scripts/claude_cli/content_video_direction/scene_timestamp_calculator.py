import re
import logging

logger = logging.getLogger(__name__)

SEARCH_WINDOW = 100


def normalize_word(word: str) -> str:
    normalized = word.lower()
    return normalized


def split_into_parts(word: str) -> list:
    parts = re.split(r'(\W)', word)
    return [p for p in parts if p]


def match_parts(word_parts: list, transcript: list, start_idx: int) -> tuple:
    limit = min(start_idx + SEARCH_WINDOW, len(transcript))
    first_idx = None
    last_idx = start_idx

    for part in word_parts:
        norm_part = normalize_word(part)
        if not norm_part:
            continue

        for i in range(last_idx, limit):
            if normalize_word(transcript[i]['word']) == norm_part:
                if first_idx is None:
                    first_idx = i
                last_idx = i + 1
                break
        else:
            logger.debug(f"Part '{part}' not found in transcript range [{start_idx}:{limit}]")
            return False, None, None

    return True, first_idx, last_idx - 1 if last_idx > start_idx else None


def match_narration_to_transcript(narration: str, transcript: list, start_index: int = 0) -> tuple:
    words = narration.split()
    start_ms = None
    end_ms = None
    idx = start_index
    matched = 0
    total = 0

    for word in words:
        norm_word = normalize_word(word)
        if not norm_word:
            continue

        total += 1
        limit = min(idx + SEARCH_WINDOW, len(transcript))
        found = False
        parts = split_into_parts(word)

        if len(parts) > 1:
            ok, first_idx, last_idx = match_parts(parts, transcript, idx)
            if ok and first_idx is not None:
                if start_ms is None:
                    start_ms = transcript[first_idx]['start_ms']
                end_ms = transcript[last_idx]['end_ms']
                idx = last_idx + 1
                matched += 1
                found = True

        if not found:
            for i in range(idx, limit):
                if normalize_word(transcript[i]['word']) == norm_word:
                    if start_ms is None:
                        start_ms = transcript[i]['start_ms']
                    end_ms = transcript[i]['end_ms']
                    idx = i + 1
                    matched += 1
                    found = True
                    break

        if not found:
            logger.debug(f"Word '{word}' (normalized: '{norm_word}') not found in transcript range [{idx}:{limit}]")

    if start_ms is None:
        logger.warning(f"No matches found for narration starting with: '{narration[:50]}...'")
        return None, None, idx, matched, total

    while idx < len(transcript):
        next_word = transcript[idx]['word']
        if next_word in '.!?':
            end_ms = transcript[idx]['end_ms']
            idx += 1
        else:
            break

    logger.debug(f"Matched {matched}/{total} words, start_ms={start_ms}, end_ms={end_ms}")
    return start_ms, end_ms, idx, matched, total
