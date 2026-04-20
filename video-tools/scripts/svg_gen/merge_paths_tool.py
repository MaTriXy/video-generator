import re
import time
from datetime import datetime

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('tools.merge_paths_tool')


def merge_paths(paths: list) -> str:
    """
    Merge multiple path strings into a single continuous path.
    Removes M (moveTo) commands from all paths except the first.

    paths: list of path d-attribute strings
           e.g. ["M 50 400 L 150 100", "M 150 100 Q 250 400 350 250", ...]

    Returns: single merged path string
    """
    func_start = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    logger.debug(f"[MERGE_PATHS] >>> FUNCTION ENTRY at {timestamp}")
    logger.debug(f"[MERGE_PATHS] Input paths type: {type(paths).__name__}")
    logger.debug(f"[MERGE_PATHS] Input paths count: {len(paths) if paths else 0}")

    if paths:
        for i, p in enumerate(paths):
            logger.debug(f"[MERGE_PATHS]   paths[{i}]: '{p[:500]}{'...' if len(p) > 500 else ''}' (len={len(p)})")

    logger.debug(f"[MERGE_PATHS] Step 1: Checking for empty paths list...")
    if not paths:
        func_elapsed = time.time() - func_start
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.debug(f"[MERGE_PATHS] Paths list is empty, returning ''")
        logger.debug(f"[MERGE_PATHS] Total function time: {func_elapsed*1000:.2f}ms")
        logger.debug(f"[MERGE_PATHS] <<< FUNCTION EXIT at {end_timestamp}")
        return ""

    logger.debug(f"[MERGE_PATHS] Step 2: Checking for single path...")
    if len(paths) == 1:
        result = paths[0].strip()
        func_elapsed = time.time() - func_start
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.debug(f"[MERGE_PATHS] Single path, returning stripped: '{result[:500]}{'...' if len(result) > 500 else ''}'")
        logger.debug(f"[MERGE_PATHS] Total function time: {func_elapsed*1000:.2f}ms")
        logger.debug(f"[MERGE_PATHS] <<< FUNCTION EXIT at {end_timestamp}")
        return result

    logger.debug(f"[MERGE_PATHS] Step 3: Starting merge of {len(paths)} paths...")
    merge_start = time.time()

    merged = [paths[0].strip()]
    logger.debug(f"[MERGE_PATHS] First path (kept as-is): '{merged[0][:500]}{'...' if len(merged[0]) > 500 else ''}'")

    for i, path in enumerate(paths[1:], start=1):
        logger.debug(f"[MERGE_PATHS] Processing path[{i}]...")
        stripped = path.strip()
        logger.debug(f"[MERGE_PATHS]   Original: '{stripped[:500]}{'...' if len(stripped) > 500 else ''}'")

        # Remove leading M/m command with its coordinates
        # Matches: "M 100 200", "M100 200", "m 100 200"
        original_len = len(stripped)
        stripped = re.sub(r'^[Mm]\s*[-\d.]+\s+[-\d.]+\s*', '', stripped)
        removed_chars = original_len - len(stripped)
        logger.debug(f"[MERGE_PATHS]   After M removal: '{stripped[:500]}{'...' if len(stripped) > 500 else ''}' (removed {removed_chars} chars)")

        if stripped:
            merged.append(stripped)
            logger.debug(f"[MERGE_PATHS]   Added to merged list (now {len(merged)} items)")
        else:
            logger.debug(f"[MERGE_PATHS]   Skipped (empty after M removal)")

    merge_elapsed = time.time() - merge_start
    logger.debug(f"[MERGE_PATHS] Merge loop completed in {merge_elapsed*1000:.2f}ms")

    logger.debug(f"[MERGE_PATHS] Step 4: Joining {len(merged)} path segments...")
    result = ' '.join(merged)

    func_elapsed = time.time() - func_start
    end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    logger.debug(f"[MERGE_PATHS] Result type: {type(result).__name__}")
    logger.debug(f"[MERGE_PATHS] Result length: {len(result)} chars")
    logger.debug(f"[MERGE_PATHS] Result preview: '{result[:500]}{'...' if len(result) > 500 else ''}'")
    logger.debug(f"[MERGE_PATHS] Total function time: {func_elapsed*1000:.2f}ms")
    logger.debug(f"[MERGE_PATHS] <<< FUNCTION EXIT at {end_timestamp}")

    return result
