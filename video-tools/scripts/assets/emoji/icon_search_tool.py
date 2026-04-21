"""
Icon search tool - MCP tool interface.
Provides batch APIs and tool functions consumed by assets_controller.

All search logic lives in icon_search_engine.py.
This file is the public API layer.
"""

import time

from scripts.logging_config import get_utility_logger
from scripts.assets.emoji.icon_search_engine import (
    ensure_index_loaded,
    initialize_all_indexes,
    get_icon_svg,
    search_icons,
    decode_icon_info,
    get_index,
    get_libraries,
)

logger = get_utility_logger('tools.icon_search_tool')


# Legacy alias for backward compatibility
initialize_icon_index = initialize_all_indexes


def list_matching_icons(library: str = "", name_query: str = "", max_results: int = 50) -> dict:
    """
    List icon names matching the given criteria.

    Args:
        library: Library symbol prefix (e.g., "fa", "gi", "md", "mdi"). Case-insensitive.
        name_query: String to match in icon names. Case-insensitive.
        max_results: Maximum number of icons to return (default 50).

    Returns:
        Dict with highPriority and mediumPriority icon name lists.
    """
    logger.info(f"[ICON_SEARCH_TOOL] Listing icons - library: '{library}', name_query: '{name_query}', max: {max_results}")

    matching_icons = search_icons(name_query=name_query, library=library, max_results=max_results)

    total = len(matching_icons.get("highPriority", [])) + len(matching_icons.get("mediumPriority", []))
    logger.info(f"[ICON_SEARCH_TOOL] Found {total} matching icons from cache")
    return matching_icons


def icon_search_tool(icon_name: str, icon_description: str) -> str:
    """
    Search for an icon by name and return its SVG.

    Args:
        icon_name: Name of the icon to search for (exact match first, then partial)
        icon_description: Description hint (currently unused)

    Returns:
        SVG string of the icon or error message
    """
    logger.info(f"[ICON_SEARCH_TOOL] Searching for icon: {icon_name}, description: {icon_description}")

    try:
        ensure_index_loaded()
        index = get_index()

        if not index:
            error_msg = "No icons found. Please ensure react-icons or @iconify/json is installed."
            logger.error(f"[ICON_SEARCH_TOOL] {error_msg}")
            return f"Error: {error_msg}"

        # First try exact match (O(1) lookup)
        if icon_name in index:
            library, source = decode_icon_info(index[icon_name])
            logger.info(f"[ICON_SEARCH_TOOL] Exact match found: {icon_name} from {source}")
            return get_icon_svg(icon_name)

        # If no exact match, search for partial match (case-insensitive)
        icon_name_lower = icon_name.lower()
        for name in index:
            if icon_name_lower in name.lower():
                logger.info(f"[ICON_SEARCH_TOOL] Partial match found: {name}")
                return get_icon_svg(name)

        error_msg = f"No icons matching '{icon_name}' found"
        logger.warning(f"[ICON_SEARCH_TOOL] {error_msg}")
        return f"Error: {error_msg}"

    except Exception as e:
        error_msg = f"Icon search failed for '{icon_name}': {str(e)}"
        logger.error(f"[ICON_SEARCH_TOOL] {error_msg}")
        return f"Error: {error_msg}"


# ============================================================================
# BATCH FUNCTIONS FOR MCP TOOLS
# ============================================================================

def get_icons_batch(icon_names: list[str]) -> list[dict]:
    """
    Get multiple icons efficiently from pre-built index.
    Single index load, then O(1) lookup per icon.

    Args:
        icon_names: List of icon names to retrieve

    Returns:
        List of dicts with icon_name and result (SVG or error)
    """
    start_time = time.time()

    ensure_index_loaded()
    index = get_index()

    if not index:
        error_msg = "No icons found. Please ensure react-icons or @iconify/json is installed."
        return [{"icon_name": name, "result": f"Error: {error_msg}"} for name in icon_names]

    results = []
    for idx, icon_name in enumerate(icon_names):
        q_start = time.time()
        match_type = None

        # Try exact match first (O(1))
        if icon_name in index:
            match_type = "exact"
            results.append({
                "icon_name": icon_name,
                "result": get_icon_svg(icon_name)
            })
        else:
            # Try partial match (case-insensitive)
            icon_name_lower = icon_name.lower()
            found = False
            for name in index:
                if icon_name_lower in name.lower():
                    match_type = f"partial->{name}"
                    results.append({
                        "icon_name": icon_name,
                        "result": get_icon_svg(name)
                    })
                    found = True
                    break

            if not found:
                match_type = "none"
                results.append({
                    "icon_name": icon_name,
                    "result": f"Error: No icon matching '{icon_name}' found"
                })

        q_ms = (time.time() - q_start) * 1000
        logger.debug(f"[GET_ICONS_BATCH] icon {idx+1}/{len(icon_names)} '{icon_name}' [{match_type}] in {q_ms:.2f}ms")

    elapsed = time.time() - start_time
    logger.info(f"[GET_ICONS_BATCH] Complete: {len(results)} results in {elapsed*1000:.2f}ms")
    return results


def search_icons_batch(queries: list[dict], video_style: str = "") -> list[dict]:
    """
    Search icons efficiently using pre-built index.
    Single index load, then filter for all queries.

    Args:
        queries: List of query dicts with 'name_query' key
        video_style: Optional video style name for library prioritization

    Returns:
        List of result dicts with name_query and icons list
    """
    start_time = time.time()

    logger.debug(f"[ICON_BATCH] Queries: {queries}")

    ensure_index_loaded()

    results = []
    for i, query in enumerate(queries):
        name_query = query.get("name_query", "")

        q_start = time.perf_counter()
        icons = search_icons(
            name_query=name_query,
            max_results=15,
            video_style=video_style
        )
        q_ms = (time.perf_counter() - q_start) * 1000

        icon_count = len(icons.get("highPriority", [])) + len(icons.get("mediumPriority", []))
        logger.debug(f"[ICON_BATCH] query {i+1}/{len(queries)} '{name_query}' -> {icon_count} icons (H:{len(icons.get('highPriority', []))} M:{len(icons.get('mediumPriority', []))}) in {q_ms:.4f}ms")
        results.append({
            "name_query": name_query,
            "icons": icons
        })

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"[ICON_BATCH] SEARCH_ICONS_BATCH COMPLETE: {len(results)} results in {elapsed_ms:.2f}ms")

    return results


def search_icons_with_svg_batch(queries: list[dict], video_style: str = "") -> list[dict]:
    start_time = time.time()

    logger.debug(f"[ICON_BATCH_V2] Queries: {queries}")

    ensure_index_loaded()

    results = []
    for i, query in enumerate(queries):
        name_query = query.get("name_query", "")

        q_start = time.perf_counter()
        icons = search_icons(
            name_query=name_query,
            max_results=15,
            video_style=video_style
        )
        q_ms = (time.perf_counter() - q_start) * 1000

        # Resolve SVGs for all matched icon names
        icons_with_svg = {}
        for priority in ("highPriority", "mediumPriority"):
            icon_names = icons.get(priority, [])
            icons_with_svg[priority] = []
            for icon_name in icon_names:
                svg = get_icon_svg(icon_name)
                icons_with_svg[priority].append({
                    "icon_name": icon_name,
                    "svg": svg
                })

        icon_count = len(icons_with_svg.get("highPriority", [])) + len(icons_with_svg.get("mediumPriority", []))
        logger.debug(f"[ICON_BATCH_V2] query {i+1}/{len(queries)} '{name_query}' -> {icon_count} icons in {q_ms:.4f}ms")
        results.append({
            "name_query": name_query,
            "icons": icons_with_svg
        })

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(f"[ICON_BATCH_V2] COMPLETE: {len(results)} results in {elapsed_ms:.2f}ms")

    return results


def get_available_libraries() -> dict:
    """
    Get list of all available libraries from both sources.

    Returns:
        Dict with library lists and counts
    """
    ensure_index_loaded()
    index = get_index()

    # Separate libraries by source
    iconify_libs = []
    react_libs = []

    seen = set()
    for encoded in index.values():
        lib, source = decode_icon_info(encoded)
        if lib not in seen:
            seen.add(lib)
            if source == "iconify":
                iconify_libs.append(lib)
            else:
                react_libs.append(lib)

    return {
        "react-icons": react_libs,
        "iconify": iconify_libs,
        "total_libraries": len(get_libraries()),
        "total_icons": len(index)
    }


def get_cached_libraries() -> list[str]:
    """Get list of available libraries from cache."""
    ensure_index_loaded()
    return get_libraries()


def get_icon_from_index(icon_name: str) -> dict | None:
    """
    Get icon data directly from index by exact name.
    Returns: icon data dict or None if not found
    """
    ensure_index_loaded()
    index = get_index()
    encoded = index.get(icon_name)
    if encoded is not None:
        library, source = decode_icon_info(encoded)
        return {"library": library, "source": source}
    return None
