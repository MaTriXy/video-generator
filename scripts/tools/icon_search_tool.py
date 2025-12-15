import os
import re
from typing import Optional
from pathlib import Path
import json
import html
from xml.etree.ElementTree import Element, SubElement, tostring

from scripts.logging_config import get_utility_logger
from scripts.utility.tool_metrics import track_tool_call

logger = get_utility_logger('tools.icon_search_tool')

# React Icons library path
REACT_ICONS_PATH = os.path.join(os.getcwd(), "node_modules", "react-icons")


def genicon_json_to_svg(json_text: str, size: int = 24, color: str = "currentColor", extra_attrs: dict | None = None) -> str:
    data = json.loads(json_text)

    def build_el(node, parent=None):
        tag = node.get("tag")
        if tag is None:
            return
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

    # Ensure basic svg attributes (size, fill, xmlns)
    if root.tag != "svg":
        # Wrap if necessary (very rare)
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

def _get_available_libraries() -> list[str]:
    """Get all available icon library directories."""
    if not os.path.exists(REACT_ICONS_PATH):
        return []

    libraries = []
    for item in os.listdir(REACT_ICONS_PATH):
        item_path = os.path.join(REACT_ICONS_PATH, item)
        if os.path.isdir(item_path) and not item.startswith('.') and not item.startswith('_'):
            libraries.append(item)
    return libraries


def _read_library_index(library_name: str) -> str | None:
    """Read the index.js content for a library. Returns None if not found."""
    index_file = os.path.join(REACT_ICONS_PATH, library_name, "index.js")
    if not os.path.exists(index_file):
        logger.warning(f"[ICON_SEARCH_TOOL] index.js not found for library {library_name}")
        return None

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"[ICON_SEARCH_TOOL] Error reading index.js for {library_name}: {e}")
        return None

def _extract_icon_names_from_content(content: str) -> list[str]:
    """Extract only icon names from library content (lightweight)."""
    pattern = r'module\.exports\.(\w+)\s*=\s*function'
    return re.findall(pattern, content)

@track_tool_call("icon_listing")
def list_matching_icons(library: str = "", name_query: str = "") -> list[str]:
    """
    List icon names matching the given criteria.

    Args:
        library: Library symbol prefix (e.g., "fa", "gi", "md"). Case-insensitive.
                 If empty, searches all libraries.
        name_query: String to match in icon names (e.g., "gear", "sun", "axe").
                    Case-insensitive. If empty, returns all icons.

    Returns:
        List of matching icon names.
    """
    logger.info(f"[ICON_SEARCH_TOOL] Listing icons - library: '{library}', name_query: '{name_query}'")

    if not os.path.exists(REACT_ICONS_PATH):
        logger.error(f"[ICON_SEARCH_TOOL] react-icons not found at {REACT_ICONS_PATH}")
        return []

    # Determine libraries to search
    if library:
        lib_lower = library.lower()
        lib_path = os.path.join(REACT_ICONS_PATH, lib_lower)
        if not os.path.isdir(lib_path):
            logger.warning(f"[ICON_SEARCH_TOOL] Library '{library}' not found")
            return []
        libraries = [lib_lower]
    else:
        libraries = _get_available_libraries()

    matching_icons = []
    for lib in libraries:
        content = _read_library_index(lib)
        if not content:
            continue

        icon_names = _extract_icon_names_from_content(content)

        if name_query:
            query_lower = name_query.lower()
            matching_icons.extend([name for name in icon_names if query_lower in name.lower()])
        else:
            matching_icons.extend(icon_names)

    logger.info(f"[ICON_SEARCH_TOOL] Found {len(matching_icons)} matching icons")
    return matching_icons

def _extract_icons_from_library(library_name: str, icon_name: str) -> list:
    lib_path = os.path.join(REACT_ICONS_PATH, library_name)
    index_file = os.path.join(lib_path, "index.js")

    matching_icons = []

    # Check if index.js exists
    if not os.path.exists(index_file):
        logger.warning(f"[ICON_SEARCH_TOOL] index.js not found for library {library_name}")
        return matching_icons

    # Read the index.js file
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all module.exports that match the icon_name (case-insensitive)
        # Pattern: module.exports.IconName = function IconName (props) { return GenIcon({...})(props); };
        pattern = r'module\.exports\.(\w+)\s*=\s*function\s+\1\s*\(props\)\s*\{\s*return\s+GenIcon\((.*?)\)\(props\);?\s*\};?'
        matches = re.findall(pattern, content, re.DOTALL)

        for icon_component_name, json_data in matches:
            # Check if the icon name matches the search query (case-insensitive)
            if icon_name.lower() in icon_component_name.lower():
                matching_icons.append({
                    'name': icon_component_name,
                    'library': library_name,
                    'json_data': json_data.strip()
                })

        logger.info(f"[ICON_SEARCH_TOOL] Found {len(matching_icons)} matching icons in library {library_name}")

    except Exception as e:
        logger.error(f"[ICON_SEARCH_TOOL] Error reading index.js for {library_name}: {e}")

    return matching_icons


@track_tool_call("icon_search")
def icon_search_tool(icon_name: str, icon_description: str) -> str:
    logger.info(f"[ICON_SEARCH_TOOL] Searching for icon: {icon_name}, description: {icon_description}")

    try:
        # Check if react-icons directory exists
        if not os.path.exists(REACT_ICONS_PATH):
            error_msg = f"react-icons not found at {REACT_ICONS_PATH}. Please install it using: npm install react-icons"
            logger.error(f"[ICON_SEARCH_TOOL] {error_msg}")
            return f"Error: {error_msg}"

        # Dynamically fetch available libraries from react-icons directory
        libraries_to_search = []

        # Read all directories in REACT_ICONS_PATH
        for item in os.listdir(REACT_ICONS_PATH):
            item_path = os.path.join(REACT_ICONS_PATH, item)
            # Only include directories (ignore files like package.json, README.md, etc.)
            if os.path.isdir(item_path) and not item.startswith('.') and not item.startswith('_'):
                libraries_to_search.append(item)

        # logger.info(f"[ICON_SEARCH_TOOL] Found {len(libraries_to_search)} icon libraries: {libraries_to_search}")

        # Search for all matching icons using the helper function
        matching_icons = []

        for lib in libraries_to_search:
            icons_from_lib = _extract_icons_from_library(lib, icon_name)
            matching_icons.extend(icons_from_lib)

        logger.info(f"[ICON_SEARCH_TOOL] -------------------------------------------------------")
        logger.info(f"[ICON_SEARCH_TOOL] Found {len(matching_icons)} matching icons for '{icon_name}'")

        if not matching_icons:
            error_msg = f"No icons matching '{icon_name}' found in any react-icons library. Searched {len(libraries_to_search)} libraries"
            logger.warning(f"[ICON_SEARCH_TOOL] {error_msg}")
            return f"Error: {error_msg}"
        logger.info(f"[ICON_SEARCH_TOOL] {matching_icons[0]['name']}" )
        return genicon_json_to_svg(matching_icons[0]['json_data'])

    except Exception as e:
        error_msg = f"Icon search failed for '{icon_name}': {str(e)}"
        logger.error(f"[ICON_SEARCH_TOOL] {error_msg}")
        return f"Error: {error_msg}"
