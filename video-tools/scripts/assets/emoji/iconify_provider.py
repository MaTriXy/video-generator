"""
Iconify provider module.
Handles SVG loading for @iconify/json library.

SIMPLIFIED: No index stored - just loads SVG on-demand from disk.
Index is managed centrally by icon_search_tool.py
"""

import os
import json
from functools import lru_cache

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('tools.iconify_provider')

# Path to iconify JSON data — resolved via utility to handle monorepo hoisting
from scripts.utility.node_modules import ICONIFY_JSON_PATH


def iconify_to_svg(body: str, width: int = 24, height: int = 24,
                   color: str = "currentColor", view_box: str = None) -> str:
    """
    Convert Iconify icon body to full SVG string.

    Args:
        body: SVG inner content (e.g., '<path d="..."/>')
        width: Output width (default 24)
        height: Output height (default 24)
        color: Fill color (default "currentColor")
        view_box: ViewBox string (default "0 0 {width} {height}")

    Returns:
        Complete SVG string
    """
    if view_box is None:
        view_box = f"0 0 {width} {height}"

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
    svg += f'width="{width}" height="{height}" fill="{color}">'
    svg += body
    svg += '</svg>'

    return svg


@lru_cache(maxsize=500)
def load_icon_data(icon_name: str, library: str) -> dict | None:
    """
    Load a single icon's data from disk on-demand.

    Results are cached using LRU cache for frequently accessed icons.

    Args:
        icon_name: Full icon name (e.g., "game-icons-trophy")
        library: Library prefix from index (e.g., "game-icons")

    Returns:
        Dict with body, width, height or None if not found
    """

    if ":" in icon_name:
        icon_key = icon_name.split(":", 1)[1]
    elif icon_name.startswith(library + "-"):
        icon_key = icon_name[len(library) + 1:]
    elif icon_name.lower().startswith(library.lower()):
        icon_key = icon_name[len(library):].lower()
    else:
        icon_key = icon_name

    file_path = os.path.join(ICONIFY_JSON_PATH, f"{library}.json")
    if not os.path.exists(file_path):
        logger.warning(f"[ICONIFY] Library file not found: {file_path}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Get default dimensions
        default_width = data.get('width', 24)
        default_height = data.get('height', 24)

        # Try to find in icons
        icon_info = data.get('icons', {}).get(icon_key)

        # If not found, check aliases
        if not icon_info:
            alias_info = data.get('aliases', {}).get(icon_key)
            if alias_info:
                parent_name = alias_info.get('parent')
                icon_info = data.get('icons', {}).get(parent_name)
                if icon_info:
                    # Merge alias overrides
                    icon_info = {**icon_info, **{k: v for k, v in alias_info.items() if k != 'parent'}}

        if not icon_info:
            logger.warning(f"[ICONIFY] Icon not found in library: {icon_name}")
            return None

        return {
            "body": icon_info.get('body', ''),
            "width": icon_info.get('width', default_width),
            "height": icon_info.get('height', default_height),
        }

    except Exception as e:
        logger.error(f"[ICONIFY] Error loading icon {icon_name}: {e}")
        return None


def get_svg(icon_name: str, library: str, size: int = 24, color: str = "currentColor") -> str | None:
    """
    Get SVG for an iconify icon.

    Loads icon data from disk on-demand (with LRU caching).

    Args:
        icon_name: Full icon name (e.g., "game-icons-trophy")
        library: Library prefix from index (e.g., "game-icons")
        size: Output size in pixels (default 24)
        color: Fill color (default "currentColor")

    Returns:
        SVG string or None if not found
    """
    # Load icon data from disk (cached)
    icon_data = load_icon_data(icon_name, library)
    if not icon_data:
        return None

    return iconify_to_svg(
        body=icon_data["body"],
        width=icon_data.get("width", size),
        height=icon_data.get("height", size),
        color=color
    )


def clear_cache():
    """Clear the LRU cache for icon data."""
    load_icon_data.cache_clear()
    logger.info("[ICONIFY] LRU cache cleared")


# ============================================================================
# LEGACY COMPATIBILITY - These functions are deprecated but kept for imports
# ============================================================================

def ensure_index_loaded():
    """Legacy no-op - index is now managed centrally."""
    pass


def get_index() -> dict:
    """Legacy - returns empty dict. Use icon_search_engine.get_index() instead."""
    logger.warning("[ICONIFY] get_index() is deprecated - use icon_search_tool directly")
    return {}


def get_libraries() -> list:
    """Legacy - returns empty list. Use icon_search_tool.LIBRARIES instead."""
    logger.warning("[ICONIFY] get_libraries() is deprecated - use icon_search_tool directly")
    return []


def get_library(icon_name: str) -> str | None:
    """Legacy - use icon_search_tool.decode_icon_info() instead."""
    logger.warning("[ICONIFY] get_library() is deprecated - use icon_search_tool directly")
    return None


def get_icon_count() -> int:
    """Legacy - use len(icon_search_engine.get_index()) instead."""
    logger.warning("[ICONIFY] get_icon_count() is deprecated - use icon_search_tool directly")
    return 0
