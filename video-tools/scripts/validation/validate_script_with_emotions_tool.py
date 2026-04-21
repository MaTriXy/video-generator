import os
import re
import time
from pathlib import Path
from datetime import datetime

from scripts.logging_config import get_utility_logger
from scripts.utility.file_io import write_to_file

logger = get_utility_logger('tools.validate_script_with_emotions_tool')

BRACKET_TAG_PATTERN = re.compile(r'\[[a-zA-Z][a-zA-Z\s\-]*?\]')

def validate_script_with_emotions(tagged_script: str, topic_id: str) -> dict:
    func_start = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] >>> FUNCTION ENTRY at {timestamp}")
    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] topic_id: {topic_id}")
    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Tagged script length: {len(tagged_script) if tagged_script else 0} chars")

    # Empty check on tagged script
    if not tagged_script or not tagged_script.strip():
        return _result(False, "Tagged script is empty.", [], func_start)

    # Resolve paths
    outputs_path = os.environ.get("VIDEO_GEN_OUTPUTS_PATH", "")
    if not outputs_path:
        return _result(False, "VIDEO_GEN_OUTPUTS_PATH environment variable is not set.", [], func_start)

    scripts_dir = Path(outputs_path) / topic_id / "Scripts"
    script_path = scripts_dir / "script.md"
    output_path = scripts_dir / "script-with-emotions.md"

    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Original script path: {script_path}")
    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Output path: {output_path}")

    if not script_path.exists():
        return _result(False, f"Original script not found at: {script_path}", [], func_start)

    # Read original script
    try:
        original_script = script_path.read_text(encoding="utf-8")
    except Exception as e:
        return _result(False, f"Failed to read original script: {e}", [], func_start)

    if not original_script or not original_script.strip():
        return _result(False, "Original script is empty.", [], func_start)

    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Original script length: {len(original_script)} chars")

    # Step 1: Collect all unique bracketed tags from the original
    original_tags = set(BRACKET_TAG_PATTERN.findall(original_script))
    if original_tags:
        logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Original contains {len(original_tags)} unique bracketed tag(s): {original_tags}")

    # Step 2: From tagged script, remove only brackets NOT in the original's set
    def _strip_new_tags(match):
        tag = match.group(0)
        if tag in original_tags:
            return tag  # keep — it was in the original
        return ''       # strip — it's an emotion tag the agent added

    stripped_tagged = BRACKET_TAG_PATTERN.sub(_strip_new_tags, tagged_script)

    # Step 3: Flatten both texts (collapse all whitespace including newlines)
    # This makes comparison tolerant of line-break reformatting by the agent
    flat_tagged = _flatten_whitespace(stripped_tagged)
    flat_original = _flatten_whitespace(original_script)

    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Flat tagged length: {len(flat_tagged)} chars")
    logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Flat original length: {len(flat_original)} chars")

    # Step 4: Compare flattened texts
    if flat_tagged == flat_original:
        # Step 5: Save tagged script on success
        try:
            write_to_file(str(output_path), tagged_script)
            logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Saved tagged script to: {output_path}")
        except Exception as e:
            return _result(False, f"Validation passed but failed to save: {e}", [], func_start)

        func_elapsed = time.time() - func_start
        logger.info(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] PASSED — scripts match, saved to {output_path} in {func_elapsed*1000:.2f}ms")
        return _result(True, "Your task is done. Validation is successful.", [], func_start)

    # Find first point of difference and show context
    diff_pos = _find_first_diff(flat_tagged, flat_original)

    logger.warning(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] FAILED — texts differ at character {diff_pos}")

    message = "FAILED: Text content does not match the original script. Do NOT change the text content, only add emotion tags."
    message += f"\n\nYour text:     \"...{flat_tagged[max(0,diff_pos-100):diff_pos+100]}...\""
    message += f"\nOriginal text: \"...{flat_original[max(0,diff_pos-100):diff_pos+100]}...\""

    return _result(False, message, [], func_start)


def _flatten_whitespace(text: str) -> str:
    """Collapse ALL whitespace (spaces, tabs, newlines) into single spaces and strip."""
    return re.sub(r'\s+', ' ', text).strip()


def _find_first_diff(text_a: str, text_b: str) -> int:
    """Return the character index where two strings first differ."""
    for i in range(min(len(text_a), len(text_b))):
        if text_a[i] != text_b[i]:
            return i
    return min(len(text_a), len(text_b))


def _result(success: bool, message: str, differences: list, func_start: float) -> dict:
    func_elapsed = time.time() - func_start
    end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    logger.debug(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Returning: success={success}")
    logger.debug(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] Total function time: {func_elapsed*1000:.2f}ms")
    logger.debug(f"[VALIDATE_SCRIPT_WITH_EMOTIONS] <<< FUNCTION EXIT at {end_timestamp}")

    return {
        "success": success,
        "message": message,
        "differences": differences,
    }
