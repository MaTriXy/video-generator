"""
React-icons provider module.
Handles SVG loading for react-icons library.

SIMPLIFIED: No index stored - just loads SVG on-demand from disk.
Index is managed centrally by icon_search_tool.py
"""

import os
import re
import json
from functools import lru_cache
from xml.etree.ElementTree import Element, SubElement, tostring

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('tools.react_icons_provider')

# React Icons library path — resolved via utility to handle monorepo hoisting
from scripts.utility.node_modules import REACT_ICONS_PATH


def genicon_json_to_svg(json_text: str, size: int = 24, color: str = "currentColor", extra_attrs: dict | None = None) -> str:
    """
    Convert GenIcon JSON structure to SVG string.

    Args:
        json_text: JSON string from react-icons GenIcon data
        size: Output size in pixels (default 24)
        color: Fill color (default "currentColor")
        extra_attrs: Additional attributes to add to SVG element

    Returns:
        Complete SVG string
    """
    data = json.loads(json_text)

    def build_el(node, parent=None):
        tag = node.get("tag")
        if tag is None:
            return None
        # Root <svg>
        if parent is None and tag != "svg":
            root = Element("svg", {"xmlns": "http://www.w3.org/2000/svg"})
            build_el(node, root)
            return root

        el = Element(tag) if parent is None else SubElement(parent, tag)

        # Apply attributes
        for k, v in (node.get("attr") or {}).items():
            if v is None:
                continue
            el.set(k, str(v))

        # Recurse for children
        for child in (node.get("child") or []):
            build_el(child, el)

        return el

    root = build_el(data)

    # Handle case where build_el returns None (invalid data)
    if root is None:
        logger.warning(f"[REACT_ICONS] Invalid icon data - no tag found")
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}"></svg>'

    # Ensure basic svg attributes (size, fill, xmlns)
    if root.tag != "svg":
        wrap = Element("svg", {"xmlns": "http://www.w3.org/2000/svg"})
        wrap.append(root)
        root = wrap

    # width/height default to `size`, but keep viewBox from data if present
    root.set("width", str(size))
    root.set("height", str(size))
    # If no fill or stroke specified, default to currentColor like react-icons
    if "fill" not in root.attrib and "stroke" not in root.attrib:
        root.set("fill", color)
    # Ensure xmlns present
    if "xmlns" not in root.attrib:
        root.set("xmlns", "http://www.w3.org/2000/svg")

    # Add any extra attrs
    if extra_attrs:
        for k, v in extra_attrs.items():
            root.set(k, str(v))

    # Serialize
    svg_bytes = tostring(root, encoding="unicode", method="xml")
    return svg_bytes


@lru_cache(maxsize=500)
def load_icon_data(icon_name: str, library: str) -> str | None:
    """
    Load a single icon's JSON data from disk on-demand.

    Results are cached using LRU cache for frequently accessed icons.

    Args:
        icon_name: Icon name (e.g., "FaHome")
        library: Library name (e.g., "fa")

    Returns:
        JSON string for GenIcon or None if not found
    """
    index_file = os.path.join(REACT_ICONS_PATH, library, "index.js")
    if not os.path.exists(index_file):
        logger.warning(f"[REACT_ICONS] Library file not found: {index_file}")
        return None

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract just this icon's GenIcon data
        pattern = rf'module\.exports\.{re.escape(icon_name)}\s*=\s*function\s+{re.escape(icon_name)}\s*\(props\)\s*\{{\s*return\s+GenIcon\((.*?)\)\(props\);?\s*\}};?'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()

        logger.warning(f"[REACT_ICONS] Icon not found in library: {icon_name}")
        return None

    except Exception as e:
        logger.error(f"[REACT_ICONS] Error loading icon {icon_name}: {e}")
        return None


def get_svg(icon_name: str, size: int = 24, color: str = "currentColor") -> str | None:
    """
    Get SVG for a react-icons icon.

    Loads icon data from disk on-demand (with LRU caching).
    Library is inferred from icon name prefix.

    Args:
        icon_name: Name of the icon (e.g., "FaHome")
        size: Output size in pixels (default 24)
        color: Fill color (default "currentColor")

    Returns:
        SVG string or None if not found
    """
    # Infer library from icon name prefix
    # React-icons naming convention: FaHome -> fa, MdHome -> md, etc.
    library = _infer_library(icon_name)
    if not library:
        logger.warning(f"[REACT_ICONS] Could not infer library for: {icon_name}")
        return None

    # Load icon data from disk (cached)
    json_data = load_icon_data(icon_name, library)
    if not json_data:
        return None

    return genicon_json_to_svg(json_data, size=size, color=color)


def _infer_library(icon_name: str) -> str | None:
    """
    Infer library name from icon name.
    React-icons uses prefixes like Fa, Md, Io, etc.
    """
    # Common prefix mappings
    prefix_map = {
        'Fa': 'fa',      # Font Awesome
        'Md': 'md',      # Material Design
        'Io': 'io',      # Ionicons
        'Io5': 'io5',    # Ionicons 5
        'Ti': 'ti',      # Typicons
        'Go': 'go',      # Github Octicons
        'Fi': 'fi',      # Feather
        'Gi': 'gi',      # Game Icons
        'Wi': 'wi',      # Weather Icons
        'Di': 'di',      # Devicons
        'Ai': 'ai',      # Ant Design
        'Bs': 'bs',      # Bootstrap
        'Ri': 'ri',      # Remix Icons
        'Fc': 'fc',      # Flat Color
        'Gr': 'gr',      # Grommet
        'Hi': 'hi',      # Hero Icons
        'Hi2': 'hi2',    # Hero Icons 2
        'Si': 'si',      # Simple Icons
        'Sl': 'sl',      # Simple Line
        'Im': 'im',      # IcoMoon
        'Bi': 'bi',      # BoxIcons
        'Cg': 'cg',      # css.gg
        'Vsc': 'vsc',    # VS Code
        'Tb': 'tb',      # Tabler
        'Tfi': 'tfi',    # Themify
        'Rx': 'rx',      # Radix
        'Pi': 'pi',      # Phosphor
        'Lia': 'lia',    # Icons8 Line Awesome
        'Lu': 'lu',      # Lucide
        'Ci': 'ci',      # Circum Icons
    }

    # Try exact prefix match (longest first)
    for prefix in sorted(prefix_map.keys(), key=len, reverse=True):
        if icon_name.startswith(prefix):
            return prefix_map[prefix]

    # Fallback: try lowercase first 2 chars
    if len(icon_name) >= 2:
        return icon_name[:2].lower()

    return None


def clear_cache():
    """Clear the LRU cache for icon data."""
    load_icon_data.cache_clear()
    logger.info("[REACT_ICONS] LRU cache cleared")


# ============================================================================
# LEGACY COMPATIBILITY - These functions are deprecated but kept for imports
# ============================================================================

def ensure_index_loaded():
    """Legacy no-op - index is now managed centrally."""
    pass


def get_index() -> dict:
    """Legacy - returns empty dict. Use icon_search_engine.get_index() instead."""
    logger.warning("[REACT_ICONS] get_index() is deprecated - use icon_search_tool directly")
    return {}


def get_libraries() -> list:
    """Legacy - returns empty list. Use icon_search_tool.LIBRARIES instead."""
    logger.warning("[REACT_ICONS] get_libraries() is deprecated - use icon_search_tool directly")
    return []


def get_library(icon_name: str) -> str | None:
    """Legacy - use icon_search_tool.decode_icon_info() instead."""
    logger.warning("[REACT_ICONS] get_library() is deprecated - use icon_search_tool directly")
    return _infer_library(icon_name)


def get_icon_count() -> int:
    """Legacy - use len(icon_search_engine.get_index()) instead."""
    logger.warning("[REACT_ICONS] get_icon_count() is deprecated - use icon_search_tool directly")
    return 0
