#!/usr/bin/env python3
"""
Standalone icon index builder script.

Run as subprocess to build icon index without polluting main process memory.
Usage: python -m scripts.assets.build_icon_index

This script:
1. Parses all iconify JSON files (regex extraction - no full JSON parse)
2. Parses all react-icons index.js files
3. Builds combined index with integer encoding
4. Saves to binary file
5. Exits (freeing all build memory)
"""

import os
import re
import sys
import json
import time
import hashlib
import pickle

# Add root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Paths — resolved via utility to handle monorepo hoisting
from scripts.utility.node_modules import ICONIFY_JSON_PATH, REACT_ICONS_PATH, INDEX_FILE_PATH, ICONIFY_PKG_PATH

REACT_ICONS_IGNORED = {
    'pi', 'ti', 'lia', 'gr', 'vsc', 'im', 'si', 'sl', 'fc',
    'fi', 'gi', 'lu', 'rx', 'fa6', 'fa', 'tb', 'ri', 'ci',
    'bi', 'bs', 'hi', 'hi2', 'ai'
}

# Common words to exclude from word index (too many matches)
STOP_WORDS = {'icon', 'icons', 'outline', 'solid', 'fill', 'filled', 'line', 'regular', 'bold', 'thin', 'light', 'sharp', 'round', 'rounded'}


def tokenize_icon_name(icon_name: str, library: str) -> set[str]:
    """
    Extract searchable tokens from an icon name.
    Returns a set of lowercase words.

    Example: "fa-brain-circuit" -> {"brain", "circuit"}
    """
    # Remove library prefix if present
    name = icon_name
    if name.startswith(library + "-"):
        name = name[len(library) + 1:]
    elif name.startswith(library):
        name = name[len(library):]

    # Split on common delimiters: dash, underscore, camelCase
    # First replace dashes/underscores with spaces
    name = name.replace("-", " ").replace("_", " ")

    # Handle camelCase: insert space before uppercase letters
    result = []
    for char in name:
        if char.isupper() and result and result[-1] != ' ':
            result.append(' ')
        result.append(char.lower())
    name = ''.join(result)

    # Split into words and filter
    words = set()
    for word in name.split():
        word = word.strip()
        # Skip empty, single-char, numeric-only, and stop words
        if len(word) > 1 and not word.isdigit() and word not in STOP_WORDS:
            words.add(word)

    return words

# Try to use msgpack for smaller/faster serialization, fall back to pickle
try:
    import msgpack
    USE_MSGPACK = True
except ImportError:
    USE_MSGPACK = False


def get_node_modules_version() -> str:
    """
    Get a version hash based on node_modules state.
    Used to invalidate index when packages are updated.
    """
    version_parts = []

    # Check @iconify/json package.json
    if os.path.exists(ICONIFY_PKG_PATH):
        with open(ICONIFY_PKG_PATH, 'r') as f:
            data = json.load(f)
            version_parts.append(f"iconify:{data.get('version', 'unknown')}")

    # Check react-icons package.json
    react_pkg = os.path.join(REACT_ICONS_PATH, "package.json")
    if os.path.exists(react_pkg):
        with open(react_pkg, 'r') as f:
            data = json.load(f)
            version_parts.append(f"react-icons:{data.get('version', 'unknown')}")

    # Create hash of versions
    version_str = "|".join(sorted(version_parts))
    return hashlib.md5(version_str.encode()).hexdigest()[:12]


def extract_keys_from_json_section(content: str, section_name: str) -> list[str]:
    """
    Extract top-level keys from a JSON section using character-by-character parsing.
    This avoids full JSON parsing, reducing memory usage.
    """
    keys = []

    # Find the section start: "section_name": {
    section_pattern = f'"{section_name}"\\s*:\\s*\\{{'
    match = re.search(section_pattern, content)
    if not match:
        return keys

    # Track brace depth to find section boundaries
    start_pos = match.end() - 1
    depth = 0
    section_end = len(content)

    for i in range(start_pos, len(content)):
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
            if depth == 0:
                section_end = i
                break

    section_content = content[start_pos + 1:section_end]

    # Extract top-level keys from section
    depth = 0
    in_string = False
    escape_next = False
    key_start = -1

    i = 0
    while i < len(section_content):
        char = section_content[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if char == '\\':
            escape_next = True
            i += 1
            continue

        if char == '"' and depth == 0 and not in_string:
            in_string = True
            key_start = i + 1
            i += 1
            continue

        if char == '"' and in_string:
            key_end = i
            in_string = False
            # Check if followed by colon (making this a key)
            j = i + 1
            while j < len(section_content) and section_content[j] in ' \t\n\r':
                j += 1
            if j < len(section_content) and section_content[j] == ':':
                key = section_content[key_start:key_end]
                keys.append(key)
            i = j
            continue

        if not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1

        i += 1

    return keys


def build_iconify_index() -> tuple[dict[str, str], list[str]]:
    """
    Build iconify index using regex extraction.
    Returns: (icon_index, libraries_list)
    """
    print("[BUILD] Building iconify index...")
    start_time = time.time()

    icon_index = {}
    libraries = []

    if not os.path.exists(ICONIFY_JSON_PATH):
        print(f"[BUILD] WARNING: @iconify/json not found at {ICONIFY_JSON_PATH}")
        return icon_index, libraries

    json_files = [f for f in os.listdir(ICONIFY_JSON_PATH) if f.endswith('.json')]
    print(f"[BUILD] Found {len(json_files)} iconify JSON files")

    total_icons = 0
    for idx, json_file in enumerate(json_files):
        prefix = json_file[:-5]  # Remove .json
        libraries.append(prefix)

        file_path = os.path.join(ICONIFY_JSON_PATH, json_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract icon keys
            icon_keys = extract_keys_from_json_section(content, 'icons')
            for icon_key in icon_keys:
                full_name = f"{prefix}-{icon_key}"
                icon_index[full_name] = prefix
                total_icons += 1

            # Extract alias keys
            alias_keys = extract_keys_from_json_section(content, 'aliases')
            for alias_key in alias_keys:
                full_name = f"{prefix}-{alias_key}"
                icon_index[full_name] = prefix
                total_icons += 1

            del content  # Help GC

            if (idx + 1) % 50 == 0:
                print(f"[BUILD] Processed {idx + 1}/{len(json_files)} files...")

        except Exception as e:
            print(f"[BUILD] ERROR reading {json_file}: {e}")
            continue

    elapsed = time.time() - start_time
    print(f"[BUILD] Iconify: {total_icons} icons from {len(libraries)} libraries in {elapsed:.2f}s")
    return icon_index, libraries


def build_react_icons_index() -> tuple[dict[str, str], list[str]]:
    """
    Build react-icons index.
    Returns: (icon_index, libraries_list)
    """
    print("[BUILD] Building react-icons index...")
    print(f"[BUILD] Ignoring {len(REACT_ICONS_IGNORED)} libraries")
    start_time = time.time()

    icon_index = {}
    libraries = []
    ignored_count = 0

    if not os.path.exists(REACT_ICONS_PATH):
        print(f"[BUILD] WARNING: react-icons not found at {REACT_ICONS_PATH}")
        return icon_index, libraries

    icon_pattern = re.compile(r'module\.exports\.(\w+)\s*=\s*function')

    for item in os.listdir(REACT_ICONS_PATH):
        item_path = os.path.join(REACT_ICONS_PATH, item)
        if os.path.isdir(item_path) and not item.startswith('.') and not item.startswith('_'):
            if item in REACT_ICONS_IGNORED:
                ignored_count += 1
                continue
            libraries.append(item)

    print(f"[BUILD] Found {len(libraries)} react-icons libraries (skipped {ignored_count} duplicates)")

    total_icons = 0
    for lib in libraries:
        index_file = os.path.join(REACT_ICONS_PATH, lib, "index.js")
        if not os.path.exists(index_file):
            continue

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()

            icon_names = icon_pattern.findall(content)
            for icon_name in icon_names:
                icon_index[icon_name] = lib
                total_icons += 1

            del content

        except Exception as e:
            print(f"[BUILD] ERROR reading {lib}: {e}")
            continue

    elapsed = time.time() - start_time
    print(f"[BUILD] React-icons: {total_icons} icons from {len(libraries)} libraries in {elapsed:.2f}s")
    return icon_index, libraries


def build_combined_index() -> dict:
    """
    Build the complete combined index with integer encoding.

    Returns dict with:
        - version: str (for invalidation)
        - libraries: list[str] (library lookup table)
        - index: dict[str, int] (icon_name -> encoded_int)
    """
    print("[BUILD] " + "=" * 50)
    print("[BUILD] ICON INDEX BUILDER")
    print("[BUILD] " + "=" * 50)

    start_time = time.time()

    # Get version for invalidation
    version = get_node_modules_version()
    print(f"[BUILD] Version hash: {version}")

    # Build provider indexes
    iconify_index, iconify_libs = build_iconify_index()
    react_index, react_libs = build_react_icons_index()

    # Build library lookup table
    libraries = []
    library_to_id = {}

    def register_library(lib: str) -> int:
        if lib in library_to_id:
            return library_to_id[lib]
        lib_id = len(libraries)
        libraries.append(lib)
        library_to_id[lib] = lib_id
        return lib_id

    # Build combined index with integer encoding
    # Encoding: value = library_id * 2 + source_bit (0=iconify, 1=react-icons)
    print("[BUILD] Building combined index with integer encoding...")

    combined_index = {}
    word_index = {}  # word -> list of icon names

    def add_to_word_index(icon_name: str, library: str):
        """Add icon to word index for each of its tokens."""
        tokens = tokenize_icon_name(icon_name, library)
        for token in tokens:
            if token not in word_index:
                word_index[token] = []
            word_index[token].append(icon_name)

    # Add iconify icons (source_bit = 0)
    for icon_name, library in iconify_index.items():
        lib_id = register_library(library)
        combined_index[icon_name] = lib_id << 1  # lib_id * 2 + 0
        add_to_word_index(icon_name, library)

    # Add react-icons (source_bit = 1, overwrites duplicates)
    for icon_name, library in react_index.items():
        lib_id = register_library(library)
        combined_index[icon_name] = (lib_id << 1) | 1  # lib_id * 2 + 1
        add_to_word_index(icon_name, library)

    elapsed = time.time() - start_time

    print(f"[BUILD] " + "-" * 50)
    print(f"[BUILD] COMPLETE")
    print(f"[BUILD] Total icons: {len(combined_index)}")
    print(f"[BUILD] Total libraries: {len(libraries)}")
    print(f"[BUILD] Unique words indexed: {len(word_index)}")
    print(f"[BUILD] Build time: {elapsed:.2f}s")
    print(f"[BUILD] " + "-" * 50)

    return {
        "version": version,
        "libraries": libraries,
        "index": combined_index,
        "word_index": word_index
    }


def save_index(data: dict, path: str):
    """Save index to binary file."""
    print(f"[BUILD] Saving index to {path}...")

    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if USE_MSGPACK:
        with open(path, 'wb') as f:
            msgpack.pack(data, f)
        print("[BUILD] Saved using msgpack")
    else:
        with open(path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        print("[BUILD] Saved using pickle")

    # Report file size
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"[BUILD] Index file size: {size_mb:.2f} MB")


def main():
    """Main entry point for subprocess execution."""
    try:
        data = build_combined_index()
        save_index(data, INDEX_FILE_PATH)
        print("[BUILD] SUCCESS")
        sys.exit(0)
    except Exception as e:
        print(f"[BUILD] FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
