"""
Icon search engine - Core search logic.
Handles index loading, searching, and video style prioritization.

OPTIMIZED ARCHITECTURE:
- Uses pre-built index file (icon_index.bin) for minimal memory
- Index is built by subprocess to avoid memory pollution
- Single combined index with integer library IDs
- SVG data loaded on-demand from providers
"""

import os
import sys
import json
import time
import pickle
import hashlib
import subprocess

from scripts.logging_config import get_utility_logger
from scripts.assets.emoji import react_icons_provider, iconify_provider
from scripts.assets.video_style_config import VIDEO_STYLE_CONFIG, DEFAULT_STYLE

logger = get_utility_logger('tools.icon_search_engine')

# Paths — resolved via utility to handle monorepo hoisting
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.utility.node_modules import INDEX_FILE_PATH, REACT_ICONS_PATH, ICONIFY_PKG_PATH, LIBRARY_ICONS_FILE_PATH

# Try msgpack for faster loading
try:
    import msgpack
    USE_MSGPACK = True
except ImportError:
    USE_MSGPACK = False

# Library lookup table - loaded from index file
LIBRARIES: list[str] = []

# Combined index cache - loaded from index file
# Format: {icon_name: encoded_int}
# Encoding: encoded_int = library_id * 2 + source_bit (0=iconify, 1=react-icons)
_COMBINED_INDEX: dict[str, int] = {}
_COMBINED_INDEX_BUILT: bool = False
_INDEX_VERSION: str = ""

# Word index for fast search - loaded from index file
# Format: {word: set[icon_name]}
_WORD_INDEX: dict[str, set[str]] = {}

# Video style config - loaded from video_style_config.json
_VIDEO_STYLE_CONFIG: dict = {}

# Prebuilt library icon sets for video style prioritization
# Format: {library_name: set(icon_names)} - only for libraries in video style config
_LIBRARY_ICONS: dict[str, set[str]] = {}


# ============================================================================
# INDEX LOADING
# ============================================================================

def _get_expected_version() -> str:
    """Get expected version hash based on current node_modules state."""
    version_parts = []

    if os.path.exists(ICONIFY_PKG_PATH):
        try:
            with open(ICONIFY_PKG_PATH, 'r') as f:
                data = json.load(f)
                version_parts.append(f"iconify:{data.get('version', 'unknown')}")
        except Exception:
            pass

    react_pkg = os.path.join(REACT_ICONS_PATH, "package.json")
    if os.path.exists(react_pkg):
        try:
            with open(react_pkg, 'r') as f:
                data = json.load(f)
                version_parts.append(f"react-icons:{data.get('version', 'unknown')}")
        except Exception:
            pass

    version_str = "|".join(sorted(version_parts))
    return hashlib.md5(version_str.encode()).hexdigest()[:12]


def _load_index_from_file() -> bool:
    """
    Load pre-built index from file.
    Returns True if successful, False if rebuild needed.
    """
    global _COMBINED_INDEX, LIBRARIES, _INDEX_VERSION, _WORD_INDEX

    if not os.path.exists(INDEX_FILE_PATH):
        logger.info("[ICON_INDEX] Index file not found, rebuild needed")
        return False

    try:
        logger.info(f"[ICON_INDEX] Loading index from {INDEX_FILE_PATH}...")
        start_time = time.time()

        with open(INDEX_FILE_PATH, 'rb') as f:
            if USE_MSGPACK:
                data = msgpack.unpack(f, raw=False)
            else:
                data = pickle.load(f)

        # Validate version
        expected_version = _get_expected_version()
        file_version = data.get("version", "")

        if file_version != expected_version:
            logger.info(f"[ICON_INDEX] Version mismatch: file={file_version}, expected={expected_version}")
            return False

        # Load data
        LIBRARIES = data["libraries"]
        _COMBINED_INDEX = data["index"]
        _INDEX_VERSION = file_version

        # Load word index (may not exist in older index files)
        # Convert lists to sets for O(1) intersection during search
        raw_word_index = data.get("word_index", {})
        _WORD_INDEX = {word: set(icons) for word, icons in raw_word_index.items()}

        elapsed = time.time() - start_time
        logger.info(f"[ICON_INDEX] Loaded {len(_COMBINED_INDEX)} icons, {len(_WORD_INDEX)} words in {elapsed:.3f}s")
        return True

    except Exception as e:
        logger.error(f"[ICON_INDEX] Failed to load index: {e}")
        return False


def _rebuild_index_subprocess():
    """
    Rebuild index by running builder script in subprocess.
    This keeps build memory separate from main process.
    """
    logger.info("[ICON_INDEX] Spawning subprocess to rebuild index...")
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "scripts.assets.emoji.build_icon_index"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=3000  # 50 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"[ICON_INDEX] Builder failed: {result.stderr}")
            raise RuntimeError(f"Index builder failed: {result.stderr}")

        elapsed = time.time() - start_time
        logger.info(f"[ICON_INDEX] Subprocess completed in {elapsed:.2f}s")

        # Log builder output
        for line in result.stdout.strip().split('\n'):
            logger.debug(f"[BUILDER] {line}")

    except subprocess.TimeoutExpired:
        logger.error("[ICON_INDEX] Builder subprocess timed out")
        raise RuntimeError("Index builder timed out")


def ensure_index_loaded():
    """
    Ensure combined index is loaded.
    Loads from file if valid, otherwise rebuilds via subprocess.
    """
    global _COMBINED_INDEX_BUILT

    if _COMBINED_INDEX_BUILT:
        return

    logger.info("[ICON_INDEX] Initializing icon index...")

    # Try loading from file first
    if _load_index_from_file():
        _COMBINED_INDEX_BUILT = True
        return

    # Need to rebuild - run in subprocess to avoid memory pollution
    _rebuild_index_subprocess()

    # Now load the newly built file
    if not _load_index_from_file():
        raise RuntimeError("Failed to load index after rebuild")

    _COMBINED_INDEX_BUILT = True


# ============================================================================
# VIDEO STYLE CONFIG
# ============================================================================

def _load_video_style_config():
    """Load video style config from Python module. Called once at startup."""
    global _VIDEO_STYLE_CONFIG
    _VIDEO_STYLE_CONFIG = VIDEO_STYLE_CONFIG
    logger.info(f"[ICON_INDEX] Loaded video style config: {len(_VIDEO_STYLE_CONFIG.get('styles', {}))} styles")


def _get_video_style_config_hash() -> str:
    """Get hash of video style config for cache invalidation."""
    content = str(VIDEO_STYLE_CONFIG)
    return hashlib.md5(content.encode()).hexdigest()[:12]


def _build_library_icon_sets():
    """
    Load or build prebuilt icon sets for libraries in video style config.
    Tries to load from .library_icons.bin first. If not valid, builds from
    _COMBINED_INDEX and saves to file for next startup.
    """
    global _LIBRARY_ICONS

    if not _VIDEO_STYLE_CONFIG or not _COMBINED_INDEX:
        return

    # Collect all unique library names from all styles
    configured_libs = set()
    for style in _VIDEO_STYLE_CONFIG.get("styles", {}).values():
        for lib in style.get("primary_libraries", []):
            configured_libs.add(lib)
        for lib in style.get("secondary_libraries", []):
            configured_libs.add(lib)

    if not configured_libs:
        return

    config_hash = _get_video_style_config_hash()

    # Try loading from file
    if os.path.exists(LIBRARY_ICONS_FILE_PATH):
        try:
            with open(LIBRARY_ICONS_FILE_PATH, 'rb') as f:
                data = pickle.load(f)

            if data.get("config_hash") == config_hash:
                _LIBRARY_ICONS = {lib: set(icons) for lib, icons in data["library_icons"].items()}
                total_icons = sum(len(s) for s in _LIBRARY_ICONS.values())
                logger.info(f"[ICON_INDEX] Loaded library icon sets from file: {total_icons} icons across {len(_LIBRARY_ICONS)} libraries")
                return
            else:
                logger.info("[ICON_INDEX] Library icons cache outdated, rebuilding...")
        except Exception as e:
            logger.warning(f"[ICON_INDEX] Failed to load library icons cache: {e}")

    # Build from _COMBINED_INDEX
    logger.info(f"[ICON_INDEX] Building library icon sets for {len(configured_libs)} configured libraries...")
    start_time = time.time()

    _LIBRARY_ICONS = {lib: set() for lib in configured_libs}

    for icon_name, encoded in _COMBINED_INDEX.items():
        library = LIBRARIES[encoded >> 1]
        if library in configured_libs:
            _LIBRARY_ICONS[library].add(icon_name)

    elapsed = time.time() - start_time
    total_icons = sum(len(s) for s in _LIBRARY_ICONS.values())
    logger.info(f"[ICON_INDEX] Library icon sets built: {total_icons} icons across {len(configured_libs)} libraries in {elapsed:.3f}s")

    # Save to file for next startup
    try:
        save_data = {
            "config_hash": config_hash,
            "library_icons": {lib: list(icons) for lib, icons in _LIBRARY_ICONS.items()}
        }
        with open(LIBRARY_ICONS_FILE_PATH, 'wb') as f:
            pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"[ICON_INDEX] Saved library icon sets to {LIBRARY_ICONS_FILE_PATH}")
    except Exception as e:
        logger.warning(f"[ICON_INDEX] Failed to save library icons cache: {e}")


# ============================================================================
# INDEX HELPERS
# ============================================================================

def decode_icon_info(value: int) -> tuple[str, str]:
    """
    Decode an integer value to (library, source).

    Args:
        value: Encoded integer from _COMBINED_INDEX

    Returns:
        Tuple of (library_name, source_name)
    """
    library_id = value >> 1  # Same as value // 2 but faster
    source_bit = value & 1   # Same as value % 2 but faster
    library = LIBRARIES[library_id]
    source = "react-icons" if source_bit else "iconify"
    return library, source


def get_index() -> dict[str, int]:
    """Get reference to the combined index dict."""
    return _COMBINED_INDEX


def get_libraries() -> list[str]:
    """Get copy of the libraries list."""
    return LIBRARIES.copy()


# ============================================================================
# SVG RETRIEVAL
# ============================================================================

def get_icon_svg(icon_name: str, size: int = 24, color: str = "currentColor") -> str:
    """
    Get SVG for an icon from either source.

    Args:
        icon_name: Name of the icon
        size: Output size (default 24)
        color: Fill color (default "currentColor")

    Returns:
        SVG string or error message
    """
    ensure_index_loaded()

    encoded = _COMBINED_INDEX.get(icon_name)
    if encoded is None:
        return f"Error: Icon '{icon_name}' not found"

    library, source = decode_icon_info(encoded)
    logger.debug(f"[ICON_INDEX] Getting SVG for '{icon_name}' from {source}")

    if source == "react-icons":
        svg = react_icons_provider.get_svg(icon_name, size=size, color=color)
        if svg:
            return svg
        return f"Error: Failed to generate SVG for '{icon_name}'"
    elif source == "iconify":
        svg = iconify_provider.get_svg(icon_name, library, size=size, color=color)
        if svg:
            return svg
        return f"Error: Failed to generate SVG for '{icon_name}'"

    return f"Error: Unknown source '{source}' for icon '{icon_name}'"


# ============================================================================
# SEARCH
# ============================================================================

def _prioritize_by_video_style(matching_set: set, video_style: str, max_results: int) -> dict:
    """
    Prioritize matched icons by video style using prebuilt library sets.
    Round-robins across primary libraries first, then secondary, then other.

    Args:
        matching_set: Set of all matching icon names from word index
        video_style: Video style name (e.g. "minimal-blue")
        max_results: Maximum results to return (total across all tiers)

    Returns:
        Dict with highPriority and mediumPriority icon name lists
    """
    styles = _VIDEO_STYLE_CONFIG.get("styles", {})

    # Resolve video style — fall back to default
    if video_style not in styles:
        default_style = _VIDEO_STYLE_CONFIG.get("default", "")
        if default_style in styles:
            video_style = default_style
        else:
            return {"highPriority": list(matching_set)[:max_results], "mediumPriority": []}

    style_config = styles[video_style]
    primary_libs = style_config.get("primary_libraries", [])
    secondary_libs = style_config.get("secondary_libraries", [])

    high = []
    medium = []
    used = set()
    total = 0

    # Set intersection for primary libraries — keep as sets, no list() conversion
    primary_iters = {}
    for lib in primary_libs:
        lib_set = _LIBRARY_ICONS.get(lib, set())
        primary_iters[lib] = iter(matching_set & lib_set)

    # Round-robin from primary using iterators → highPriority
    while total < max_results:
        added = False
        for lib in primary_libs:
            icon = next(primary_iters[lib], None)
            if icon is not None:
                high.append(icon)
                used.add(icon)
                added = True
                total += 1
                if total >= max_results:
                    break
        if not added:
            break

    if total >= max_results:
        return {"highPriority": high, "mediumPriority": []}

    # Set intersection for secondary libraries — keep as sets
    secondary_iters = {}
    for lib in secondary_libs:
        lib_set = _LIBRARY_ICONS.get(lib, set())
        secondary_iters[lib] = iter((matching_set & lib_set) - used)

    # Round-robin from secondary using iterators → mediumPriority
    while total < max_results:
        added = False
        for lib in secondary_libs:
            icon = next(secondary_iters[lib], None)
            if icon is not None:
                medium.append(icon)
                used.add(icon)
                added = True
                total += 1
                if total >= max_results:
                    break
        if not added:
            break
        
    # If no results from primary/secondary, return from full library
    # if not high and not medium:
    #     remaining = list(matching_set)[:max_results]
    #     return {"highPriority": [], "mediumPriority": remaining}

    return {"highPriority": high, "mediumPriority": medium}


def search_icons(name_query: str = "", library: str = "", max_results: int = 50, video_style: str = "") -> dict:
    """
    Search icons using inverted word index for O(1) lookups.
    Falls back to linear scan if word index is not available.
    If video_style is provided, prioritizes results from style's primary/secondary libraries.

    Returns:
        Dict with highPriority and mediumPriority icon name lists
    """
    ensure_index_loaded()

    logger.debug(f"[ICON_INDEX] Searching: query='{name_query}', library='{library}', max={max_results}")

    query_words = name_query.lower().split() if name_query else []

    if not query_words:
        return {"highPriority": [], "mediumPriority": []}

    lib_lower = library.lower() if library else ""

    # Use word index for fast search if available
    if _WORD_INDEX:
        if len(query_words) == 1:
            icons_for_word = _WORD_INDEX.get(query_words[0], set())

            if lib_lower and icons_for_word:
                filtered = []
                for icon_name in icons_for_word:
                    encoded = _COMBINED_INDEX.get(icon_name)
                    if encoded is not None:
                        icon_library, _ = decode_icon_info(encoded)
                        if icon_library.lower() == lib_lower:
                            filtered.append(icon_name)
                matching = {"highPriority": filtered[:max_results], "mediumPriority": []}
            elif _VIDEO_STYLE_CONFIG and _LIBRARY_ICONS:
                matching = _prioritize_by_video_style(icons_for_word, video_style, max_results)
            else:
                matching = {"highPriority": list(icons_for_word)[:max_results], "mediumPriority": []}
        else:
            candidate_sets = []
            missing_word = False
            for word in query_words:
                icons_for_word = _WORD_INDEX.get(word, set())
                if not icons_for_word:
                    missing_word = True
                    break
                candidate_sets.append(icons_for_word)

            matching_set = set()
            if not missing_word and candidate_sets:
                matching_set = candidate_sets[0].copy()
                for s in candidate_sets[1:]:
                    matching_set &= s
                    if not matching_set:
                        break

            if not matching_set:
                concat_word = "".join(query_words)
                concat_icons = _WORD_INDEX.get(concat_word, set())
                if concat_icons:
                    matching_set = concat_icons.copy()

            # Filter by library if specified
            if lib_lower and matching_set:
                filtered = []
                for icon_name in matching_set:
                    encoded = _COMBINED_INDEX.get(icon_name)
                    if encoded is not None:
                        icon_library, _ = decode_icon_info(encoded)
                        if icon_library.lower() == lib_lower:
                            filtered.append(icon_name)
                matching = {"highPriority": filtered[:max_results], "mediumPriority": []}
            elif _VIDEO_STYLE_CONFIG and _LIBRARY_ICONS:
                matching = _prioritize_by_video_style(matching_set, video_style, max_results)
            else:
                matching = {"highPriority": list(matching_set)[:max_results], "mediumPriority": []}

        return matching

    # Fallback: linear scan (slow, for backwards compatibility)
    logger.warning("[ICON_INDEX] Word index not available, using slow linear scan")
    start_time = time.time()
    matching = []

    for icon_name, encoded in _COMBINED_INDEX.items():
        if lib_lower:
            icon_library, _ = decode_icon_info(encoded)
            if icon_library.lower() != lib_lower:
                continue

        icon_name_lower = icon_name.lower()
        if all(word in icon_name_lower for word in query_words):
            matching.append(icon_name)
            if max_results > 0 and len(matching) >= max_results:
                break

    elapsed = time.time() - start_time
    logger.debug(f"[ICON_INDEX] Linear scan found {len(matching)} results in {elapsed*1000:.2f}ms")
    return {"highPriority": matching, "mediumPriority": []}


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_all_indexes():
    """Initialize all icon indexes at startup."""
    logger.info("[ICON_INDEX] Initializing all icon indexes...")
    ensure_index_loaded()
    _load_video_style_config()
    _build_library_icon_sets()
    logger.info(f"[ICON_INDEX] Ready: {len(_COMBINED_INDEX)} icons, {len(LIBRARIES)} libraries")
