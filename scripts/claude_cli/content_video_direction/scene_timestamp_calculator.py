import re


def normalize_characters(text: str) -> str:
    char_map = {
        '‚': ",",
        '‛': "'",
        '`': "'",
        '´': "'",
        'ʹ': "'",
        'ʻ': "'",
        'ʼ': "'",
        'ʽ': "'",
        '"': "'", 
        '"': "'",
        '"': "'",
        '„': "'",
        '‟': "'",
        '〝': "'",
        '〞': "'",
        '«': "'",
        '»': "'",
        '–': '-',
        '—': '-',
        '―': '-',
        '−': '-',
        '‐': '-',
        '‑': '-',
        '‒': '-',
        '⁃': '-',
        '…': '...',
        '\u00A0': ' ',
        '\u2002': ' ',
        '\u2003': ' ',
        '\u2004': ' ',
        '\u2005': ' ',
        '\u2006': ' ',
        '\u2007': ' ',
        '\u2008': ' ',
        '\u2009': ' ',
        '\u200A': ' ',
        '\u202F': ' ',
        '\u205F': ' ',
        '•': '*',
        '·': '*',
        '∙': '*',
        '○': '*',
        '●': '*',
        '×': 'x',
        '÷': '/',
        '≈': '~',
        '≠': '!=',
        '≤': '<=',
        '≥': '>=',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'YEN',
        '¢': 'c',
        '½': '1/2',
        '⅓': '1/3',
        '⅔': '2/3',
        '¼': '1/4',
        '¾': '3/4',
        '⅕': '1/5',
        '⅖': '2/5',
        '⅗': '3/5',
        '⅘': '4/5',
        '⅙': '1/6',
        '⅚': '5/6',
        '⅛': '1/8',
        '⅜': '3/8',
        '⅝': '5/8',
        '⅞': '7/8',
    }
    for unicode_char, ascii_char in char_map.items():
        text = text.replace(unicode_char, ascii_char)
    return text


def normalize_for_matching(word: str) -> str:
    return normalize_characters(word).lower()


def split_word_into_parts(word: str) -> list:
    word = normalize_characters(word)
    parts = re.split(r'(\W)', word)
    return [part for part in parts if part]


def match_word_parts_in_transcript(word_parts: list, transcript: list, start_search_index: int) -> tuple:
    search_index = start_search_index
    search_limit = min(start_search_index + 100, len(transcript))
    parts_matched = 0
    for part in word_parts:
        normalized_part = normalize_for_matching(part)
        if not normalized_part:
            continue
        found_part = False
        temp_search_index = search_index
        while temp_search_index < search_limit:
            transcript_word = transcript[temp_search_index]['word']
            normalized_transcript = normalize_for_matching(transcript_word)
            if normalized_part == normalized_transcript:
                search_index = temp_search_index + 1
                parts_matched += 1
                found_part = True
                break
            temp_search_index += 1
        if not found_part:
            return False, start_search_index, 0
    return True, search_index - 1, parts_matched


def match_narration_to_transcript(narration: str, transcript: list, start_index: int = 0) -> tuple:
    narration_words = narration.split()
    start_ms = None
    end_ms = None
    transcript_index = start_index
    matched_count = 0
    total_word_count = 0
    search_start_index = start_index
    for narration_word in narration_words:
        normalized_narration_word = normalize_for_matching(narration_word)
        if not normalized_narration_word:
            continue
        total_word_count += 1
        found = False
        word_parts = split_word_into_parts(narration_word)
        has_multiple_parts = len(word_parts) > 1
        search_limit = min(transcript_index + 100, len(transcript))
        search_index = transcript_index
        if has_multiple_parts:
            parts_found, last_matched_index, parts_matched = match_word_parts_in_transcript(
                word_parts, transcript, transcript_index
            )
            if parts_found and last_matched_index >= transcript_index:
                if start_ms is None:
                    start_ms = transcript[transcript_index]['start_ms']
                    search_start_index = transcript_index
                end_ms = transcript[last_matched_index]['end_ms']
                transcript_index = last_matched_index + 1
                matched_count += parts_matched
                found = True
        if not found:
            while search_index < search_limit:
                transcript_word = transcript[search_index]['word']
                normalized_transcript_word = normalize_for_matching(transcript_word)
                if normalized_narration_word == normalized_transcript_word:
                    if start_ms is None:
                        start_ms = transcript[search_index]['start_ms']
                        search_start_index = search_index
                    end_ms = transcript[search_index]['end_ms']
                    transcript_index = search_index + 1
                    matched_count += 1
                    found = True
                    break
                else:
                    search_index += 1
        if not found:
            if start_ms is None and transcript_index < len(transcript):
                transcript_index += 1
    if start_ms is None:
        return None, None, transcript_index, matched_count, total_word_count
    return start_ms, end_ms, transcript_index, matched_count, total_word_count
