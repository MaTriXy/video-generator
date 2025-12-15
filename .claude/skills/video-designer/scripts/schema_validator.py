"""
Schema Validation Script for Video Design JSON

This script validates a video design JSON file against the rules defined in
'video-designer/references/schema-validation-rules.md'.

It checks for:
1.  JSON syntax errors.
2.  Missing or extra (forbidden) fields.
3.  Correct data types for all fields.
4.  Valid values, formats, and enum constraints.
5.  Logical consistency (e.g., timing, unique IDs).

Usage:
    python schema_validator.py <path_to_design_file.json>
"""

import json
import os
import sys
import argparse
import re
from typing import Dict, List, Any, Optional, Set
import traceback

# --- Data Classes for Issues ---

class Issue:
    """A class to represent a single validation issue."""
    def __init__(self, category: str, message: str, element_id: Optional[str] = None, path: Optional[str] = None):
        self.category = category
        self.message = message
        self.element_id = element_id
        self.path = path

    def __str__(self):
        if self.element_id:
            return f"[{self.category}] Element '{self.element_id}': {self.message}"
        return f"[{self.category}] {self.message}"

# --- Main Validation Logic ---

class SchemaValidator:
    """A class to encapsulate the validation logic."""

    # Valid path types
    VALID_PATH_TYPES = [
        "linear", "arc", "bezier", "bounce", "circular", "elliptical",
        "parabolic", "s_curve", "sine_wave", "spiral", "spline", "zigzag"
    ]

    # Valid arrow marker types
    VALID_ARROW_MARKERS = ["hollow", "fill", "line"]

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: List[Issue] = []
        self.element_ids: Set[str] = set()
        self.json_data: Optional[Dict] = None

    def validate(self):
        """Main method to run all validation checks."""
        if not os.path.exists(self.filepath):
            self.issues.append(Issue("FILE_NOT_FOUND", f"The file '{self.filepath}' does not exist."))
            return

        # 1. JSON Syntax Check
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
        except json.JSONDecodeError as e:
            error_message = (
                f"Error: {e.msg}\n"
                f"        - Location: Line {e.lineno}, Column {e.colno}\n"
                "        - Hint: The JSON structure is broken. Check for missing commas (,), misplaced brackets ([]), or braces ({}) around this line."
            )
            self.issues.append(Issue("SYNTAX_ERROR", error_message))
            self.print_issues()
            return # Stop validation if JSON is invalid

        # 2. Schema Validation
        self._validate_toplevel()
        self.print_issues()

    def _add_issue(self, category: str, message: str, element_id: Optional[str] = None, path: Optional[str] = None):
        self.issues.append(Issue(category, message, element_id, path))

    def _validate_toplevel(self):
        """Validates the top-level structure of the JSON."""
        if not isinstance(self.json_data, dict):
            self._add_issue("INVALID_TYPE", "Top-level structure must be a JSON object.")
            return

        required_fields = {
            "scene": int, "startTime": int, "endTime": int,
            "scene_description": str, "video_metadata": dict, "elements": list
        }
        self._check_fields("Top-level", self.json_data, required_fields)

        # Basic value checks
        start_time = self.json_data.get("startTime", 0)
        end_time = self.json_data.get("endTime", 0)

        if start_time < 0:
            self._add_issue("INVALID_VALUE", f"'startTime' ({start_time}) must be >= 0.")
        if end_time <= start_time:
            self._add_issue("TIMING_INVALID", f"'endTime' ({end_time}) must be > 'startTime' ({start_time}).")

        # Validate nested structures
        if "video_metadata" in self.json_data and isinstance(self.json_data["video_metadata"], dict):
            self._validate_video_metadata(self.json_data["video_metadata"])

        if "elements" in self.json_data and isinstance(self.json_data["elements"], list):
            if not self.json_data["elements"]:
                self._add_issue("INVALID_VALUE", "'elements' array cannot be empty.")
            else:
                self._validate_elements(self.json_data["elements"], start_time, end_time)

    def _validate_video_metadata(self, metadata: Dict):
        """Validates the 'video_metadata' object."""
        path = "video_metadata"
        required_fields = {
            "viewport_size": str, "canvas": dict, "layout": dict
        }
        self._check_fields(path, metadata, required_fields)

        if "viewport_size" in metadata and isinstance(metadata["viewport_size"], str):
            if not re.match(r"^\d+x\d+$", metadata["viewport_size"]):
                self._add_issue("INVALID_FORMAT", f"'{path}.viewport_size' format is invalid. Expected 'WIDTHxHEIGHT', got '{metadata['viewport_size']}'.")

        # Validate canvas
        if "canvas" in metadata and isinstance(metadata["canvas"], dict):
            self._validate_canvas(metadata["canvas"])

        # Validate layout
        if "layout" in metadata and isinstance(metadata["layout"], dict):
            self._validate_layout(metadata["layout"])

    def _validate_canvas(self, canvas: Dict):
        """Validates the 'canvas' object within video_metadata."""
        path = "video_metadata.canvas"
        required_fields = {"backgroundColor": str}
        self._check_fields(path, canvas, required_fields)

        # Validate backgroundColor format
        # TODO: Add _validate_color_format method
        # if "backgroundColor" in canvas:
        #     self._validate_color_format(canvas["backgroundColor"], "backgroundColor", path)

    def _validate_layout(self, layout: Dict):
        """Validates the 'layout' object within video_metadata."""
        path = "video_metadata.layout"
        required_fields = {"strategy": str, "description": str}
        self._check_fields(path, layout, required_fields)

        # Validate vertical_padding_percent if present (it's optional)
        if "vertical_padding_percent" in layout:
            vp_percent = layout["vertical_padding_percent"]
            if not isinstance(vp_percent, (int, float)):
                self._add_issue("INVALID_TYPE", f"Field '{path}.vertical_padding_percent' must be a number.")
            elif vp_percent < 0 or vp_percent > 100:
                self._add_issue("INVALID_VALUE", f"Field '{path}.vertical_padding_percent' ({vp_percent}) must be between 0 and 100.")

    def _validate_elements(self, elements: List[Dict], scene_start_time: int, scene_end_time: int):
        """Validates the 'elements' array."""
        for i, element in enumerate(elements):
            if not isinstance(element, dict):
                self._add_issue("INVALID_TYPE", f"Item at index {i} in 'elements' is not a JSON object.")
                continue

            element_id = element.get("id")
            if not element_id:
                self._add_issue("MISSING_REQUIRED_FIELD", f"Element at index {i} is missing 'id'.")
                element_id = f"unknown_at_index_{i}"
            elif not isinstance(element_id, str):
                self._add_issue("INVALID_TYPE", f"Element 'id' must be a string.", element_id=element_id)
            elif element_id in self.element_ids:
                self._add_issue("DUPLICATE_ID", f"Duplicate element ID found.", element_id=element_id)
            else:
                self.element_ids.add(element_id)

            self._validate_single_element(element, scene_start_time, scene_end_time, element_id)

    def _validate_single_element(self, element: Dict, scene_start_time: int, scene_end_time: int, element_id: str):
        """Validates a single element object."""
        path = f"Element '{element_id}'"
        common_required = {
            "type": str, "content": str, "zIndex": int, "timing": dict, "styles": dict
        }
        self._check_fields(path, element, common_required, element_id=element_id)

        # Validate timing
        timing = element.get("timing")
        if isinstance(timing, dict):
            self._validate_timing(timing, scene_start_time, scene_end_time, element_id)

        # Validate animation (if present)
        animation = element.get("animation")
        if isinstance(animation, dict):
            self._validate_animation(animation, scene_start_time, scene_end_time, element_id)

        # Validate styles
        styles = element.get("styles")
        if isinstance(styles, dict):
            self._validate_styles(styles, element_id)

        # Type-specific validation
        elem_type = element.get("type")
        if elem_type == "text":
            self._validate_text_element(element, element_id)
        elif elem_type in ["shape", "icon", "character"]:
            self._validate_shape_element(element, element_id)
        elif elem_type == "path":
            self._validate_path_element(element, element_id)
        elif elem_type:
            # Invalid type - flag it but continue validating common fields
            self._add_issue("INVALID_SCHEMA_TYPE",
                f"Element has invalid type '{elem_type}' (valid types: text, shape, icon, character, path). Type-specific validation cannot be performed.",
                element_id=element_id)

    def _validate_timing(self, timing: Dict, scene_start_time: int, scene_end_time: int, element_id: str):
        path = f"Element '{element_id}'.timing"
        required_fields = {"enterOn": int, "exitOn": int}
        self._check_fields(path, timing, required_fields, element_id)

        enter_on = timing.get("enterOn", 0)
        exit_on = timing.get("exitOn", 0)

        # Basic value checks
        if enter_on < 0:
            self._add_issue("INVALID_VALUE", f"'enterOn' ({enter_on}) must be >= 0.", element_id)
        if exit_on <= enter_on:
            self._add_issue("TIMING_INVALID", f"'exitOn' ({exit_on}) must be > 'enterOn' ({enter_on}).", element_id)

        # Element timing must be within scene bounds [startTime, endTime]
        if enter_on < scene_start_time:
            self._add_issue("TIMING_INVALID",
                f"'enterOn' ({enter_on}) must be >= scene 'startTime' ({scene_start_time}). "
                f"All timings must use absolute video timestamps.", element_id)
        if enter_on > scene_end_time:
            self._add_issue("TIMING_INVALID",
                f"'enterOn' ({enter_on}) cannot be greater than scene 'endTime' ({scene_end_time}).", element_id)
        if exit_on < scene_start_time:
            self._add_issue("TIMING_INVALID",
                f"'exitOn' ({exit_on}) must be >= scene 'startTime' ({scene_start_time}). "
                f"All timings must use absolute video timestamps.", element_id)
        if exit_on > scene_end_time:
            self._add_issue("TIMING_INVALID",
                f"'exitOn' ({exit_on}) cannot be greater than scene 'endTime' ({scene_end_time}).", element_id)

    def _validate_animation(self, animation: Dict, scene_start_time: int, scene_end_time: int, element_id: str):
        """Validates the 'animation' object and its actions."""
        path = f"Element '{element_id}'.animation"

        # Validate actions array if present
        if "actions" in animation:
            actions = animation.get("actions")
            if not isinstance(actions, list):
                self._add_issue("INVALID_TYPE",
                    f"Field '{path}.actions' must be an array.", element_id)
            else:
                for i, action in enumerate(actions):
                    if not isinstance(action, dict):
                        self._add_issue("INVALID_TYPE",
                            f"Item at index {i} in '{path}.actions' must be a dictionary.", element_id)
                        continue

                    # Validate action.on timing
                    if "on" not in action:
                        self._add_issue("MISSING_REQUIRED_FIELD",
                            f"Field 'on' is missing from '{path}.actions[{i}]'.", element_id)
                    else:
                        action_on = action.get("on")
                        if not isinstance(action_on, (int, float)):
                            self._add_issue("INVALID_TYPE",
                                f"Field '{path}.actions[{i}].on' must be a number.", element_id)
                        else:
                            # Action timing must be within scene bounds
                            if action_on < scene_start_time:
                                self._add_issue("TIMING_INVALID",
                                    f"'actions[{i}].on' ({action_on}) must be >= scene 'startTime' ({scene_start_time}). "
                                    f"All timings must use absolute video timestamps.", element_id)
                            if action_on > scene_end_time:
                                self._add_issue("TIMING_INVALID",
                                    f"'actions[{i}].on' ({action_on}) cannot be greater than scene 'endTime' ({scene_end_time}).", element_id)

    def _validate_styles(self, styles: Dict, element_id: str):
        """Validates the 'styles' object of an element."""
        path = f"Element '{element_id}'.styles"
        if "position" in styles:
            if not isinstance(styles["position"], dict):
                self._add_issue("INVALID_TYPE", f"Field '{path}.position' must be a dictionary.", element_id)
            else:
                position_path = f"{path}.position"
                required_position_fields = {"x": (int, float), "y": (int, float)}
                self._check_fields(position_path, styles["position"], required_position_fields, element_id)
        else:
            self._add_issue("MISSING_REQUIRED_FIELD", f"Field 'position' is missing from '{path}'.", element_id)

    def _validate_text_element(self, element: Dict, element_id: str):
        path = f"Element '{element_id}'"
        required = {"text": str, "container": dict}
        self._check_fields(path, element, required, element_id)

        # bgID is optional - can be empty string or missing
        if "bgID" in element and not isinstance(element["bgID"], str):
            self._add_issue("INVALID_TYPE", f"Field 'bgID' has type '{type(element['bgID']).__name__}', expected 'str'.", element_id)

        # Validate styles.states.default for text-specific properties
        styles = element.get("styles", {})
        states = styles.get("states", {})
        default_state = states.get("default", {})

        if not isinstance(default_state, dict):
            self._add_issue("INVALID_TYPE", "Field 'styles.states.default' must be a dictionary.", element_id)
        else:
            text_style_required = {
                "fontColor": str,
                "fontSize": (int, float),
                "textAlign": str,
                "fontWeight": (int, str),
                "lineHeight": (int, float)
            }
            default_path = f"Element '{element_id}'.styles.states.default"
            self._check_fields(default_path, default_state, text_style_required, element_id)

            # Validate fontSize value
            font_size = default_state.get("fontSize")
            if isinstance(font_size, (int, float)) and font_size <= 0:
                self._add_issue("INVALID_VALUE", f"'fontSize' ({font_size}) must be > 0.", element_id)

            # Validate textAlign enum
            text_align = default_state.get("textAlign")
            if isinstance(text_align, str) and text_align not in ["left", "center", "right"]:
                self._add_issue("INVALID_ENUM", f"'textAlign' has invalid value '{text_align}', must be one of: left, center, right.", element_id)

            # Validate lineHeight value
            line_height = default_state.get("lineHeight")
            if isinstance(line_height, (int, float)) and line_height <= 0:
                self._add_issue("INVALID_VALUE", f"'lineHeight' ({line_height}) must be > 0.", element_id)

        forbidden = ["styles.size"]
        for key in forbidden:
            if self._is_nested_key_present(element, key):
                self._add_issue("FORBIDDEN_FIELD", f"Contains forbidden field '{key}'.", element_id)

    def _validate_shape_element(self, element: Dict, element_id: str):
        path = f"Element '{element_id}'.styles"
        styles = element.get("styles", {})
        required = {"size": dict}
        self._check_fields(path, styles, required, element_id)

        if isinstance(styles.get("size"), dict):
            size_path = f"{path}.size"
            size_required = {"width": (int, float), "height": (int, float)}
            self._check_fields(size_path, styles["size"], size_required, element_id)
            if styles.get("size", {}).get("width", 0) <= 0:
                 self._add_issue("INVALID_VALUE", "'width' must be > 0.", element_id)
            if styles.get("size", {}).get("height", 0) <= 0:
                 self._add_issue("INVALID_VALUE", "'height' must be > 0.", element_id)

        forbidden = ["text", "bgID", "container"]
        for key in forbidden:
            if key in element:
                self._add_issue("FORBIDDEN_FIELD", f"Contains forbidden field '{key}'.", element_id)

    def _validate_path_element(self, element: Dict, element_id: str):
        """Validates a path element (type: 'path')."""
        path = f"Element '{element_id}'"

        # Check for either path_params OR merge_path_params (mutually exclusive)
        has_path_params = "path_params" in element
        has_merge_path_params = "merge_path_params" in element

        if has_path_params and has_merge_path_params:
            self._add_issue("INVALID_STRUCTURE",
                "Cannot have both 'path_params' and 'merge_path_params'. Use only one.", element_id)
        elif not has_path_params and not has_merge_path_params:
            self._add_issue("MISSING_REQUIRED_FIELD",
                "Must have either 'path_params' or 'merge_path_params'.", element_id, path=path)

        # Validate path_params (single path)
        if has_path_params:
            path_params = element.get("path_params")
            if not isinstance(path_params, dict):
                self._add_issue("INVALID_TYPE",
                    f"Field 'path_params' must be a dictionary, got '{type(path_params).__name__}'.", element_id)
            else:
                self._validate_single_path_params(path_params, element_id, "path_params")

        # Validate merge_path_params (composite path - array of paths)
        if has_merge_path_params:
            merge_path_params = element.get("merge_path_params")
            if not isinstance(merge_path_params, list):
                self._add_issue("INVALID_TYPE",
                    f"Field 'merge_path_params' must be an array, got '{type(merge_path_params).__name__}'.", element_id)
            elif len(merge_path_params) == 0:
                self._add_issue("INVALID_VALUE",
                    "'merge_path_params' array cannot be empty.", element_id)
            else:
                for i, path_segment in enumerate(merge_path_params):
                    if not isinstance(path_segment, dict):
                        self._add_issue("INVALID_TYPE",
                            f"Item at index {i} in 'merge_path_params' must be a dictionary.", element_id)
                    else:
                        self._validate_single_path_params(path_segment, element_id, f"merge_path_params[{i}]")

        # Validate arrow_marker (required when content mentions arrow)
        content = element.get("content", "").lower()
        has_arrow_in_content = any(keyword in content for keyword in ["arrow", "arrowhead", "arrow head", "arrow-head"])

        if has_arrow_in_content and "arrow_marker" not in element:
            self._add_issue("MISSING_REQUIRED_FIELD",
                "Field 'arrow_marker' is required when content mentions 'arrow' or 'arrowhead'.", element_id, path=path)

        if "arrow_marker" in element:
            arrow_marker = element.get("arrow_marker")
            if not isinstance(arrow_marker, str):
                self._add_issue("INVALID_TYPE",
                    f"Field 'arrow_marker' must be a string, got '{type(arrow_marker).__name__}'.", element_id)
            elif arrow_marker not in self.VALID_ARROW_MARKERS:
                self._add_issue("INVALID_ENUM",
                    f"'arrow_marker' has invalid value '{arrow_marker}', must be one of: {', '.join(self.VALID_ARROW_MARKERS)}.", element_id)

        # Path elements must have styles.size (like shape elements)
        styles = element.get("styles", {})
        if not isinstance(styles, dict):
            return  # Already validated in _validate_styles

        if "size" not in styles:
            self._add_issue("MISSING_REQUIRED_FIELD",
                "Field 'size' is missing from 'styles'.", element_id, path=f"Element '{element_id}'.styles")
        elif isinstance(styles["size"], dict):
            size_path = f"Element '{element_id}'.styles.size"
            size_required = {"width": (int, float), "height": (int, float)}
            self._check_fields(size_path, styles["size"], size_required, element_id)
            if styles.get("size", {}).get("width", 0) <= 0:
                self._add_issue("INVALID_VALUE", "'width' must be > 0.", element_id)
            if styles.get("size", {}).get("height", 0) <= 0:
                self._add_issue("INVALID_VALUE", "'height' must be > 0.", element_id)

        # Forbidden fields for path elements
        forbidden = ["text", "bgID", "container"]
        for key in forbidden:
            if key in element:
                self._add_issue("FORBIDDEN_FIELD", f"Contains forbidden field '{key}'.", element_id)

    def _validate_single_path_params(self, path_params: Dict, element_id: str, params_path: str):
        """Validates a single path_params object (used for both path_params and merge_path_params items)."""
        # Check for required 'type' field
        if "type" not in path_params:
            self._add_issue("MISSING_REQUIRED_FIELD",
                f"Field 'type' is missing from '{params_path}'.", element_id)
            return

        path_type = path_params.get("type")
        if not isinstance(path_type, str):
            self._add_issue("INVALID_TYPE",
                f"Field '{params_path}.type' must be a string, got '{type(path_type).__name__}'.", element_id)
            return
        elif path_type not in self.VALID_PATH_TYPES:
            self._add_issue("INVALID_ENUM",
                f"'{params_path}.type' has invalid value '{path_type}', must be one of: {', '.join(self.VALID_PATH_TYPES)}.", element_id)
            return

        # Type-specific required fields validation
        type_required_fields = {
            "linear": {"start_x": (int, float), "start_y": (int, float), "end_x": (int, float), "end_y": (int, float)},
            "arc": {"start_x": (int, float), "start_y": (int, float), "end_x": (int, float), "end_y": (int, float), "radius": (int, float)},
            "bezier": {"start_x": (int, float), "start_y": (int, float), "cp1_x": (int, float), "cp1_y": (int, float),
                      "cp2_x": (int, float), "cp2_y": (int, float), "end_x": (int, float), "end_y": (int, float)},
            "bounce": {"start_x": (int, float), "start_y": (int, float), "end_x": (int, float),
                      "ground_y": (int, float), "initial_height": (int, float), "bounces": (int, float)},
            "circular": {"center_x": (int, float), "center_y": (int, float), "radius": (int, float)},
            "elliptical": {"center_x": (int, float), "center_y": (int, float), "radius_x": (int, float), "radius_y": (int, float)},
            "parabolic": {"start_x": (int, float), "start_y": (int, float), "end_x": (int, float), "end_y": (int, float), "arc_height": (int, float)},
            "sine_wave": {"start_x": (int, float), "start_y": (int, float), "wavelength": (int, float), "amplitude": (int, float), "cycles": (int, float)},
            "spiral": {"center_x": (int, float), "center_y": (int, float), "max_radius": (int, float), "revolutions": (int, float)},
            "s_curve": {"start_x": (int, float), "start_y": (int, float), "end_x": (int, float), "end_y": (int, float)},
            "spline": {"points": list},
            "zigzag": {"start_x": (int, float), "start_y": (int, float), "segment_length": (int, float), "amplitude": (int, float), "segments": (int, float)}
        }

        if path_type in type_required_fields:
            required_fields = type_required_fields[path_type]
            self._check_fields(params_path, path_params, required_fields, element_id)

            # Special validation for spline points
            if path_type == "spline" and "points" in path_params:
                points = path_params["points"]
                if isinstance(points, list):
                    if len(points) < 2:
                        self._add_issue("INVALID_VALUE",
                            f"'{params_path}.points' must have at least 2 points.", element_id)
                    for i, point in enumerate(points):
                        if not isinstance(point, list) or len(point) != 2:
                            self._add_issue("INVALID_TYPE",
                                f"'{params_path}.points[{i}]' must be an array of [x, y] coordinates.", element_id)
                        elif not all(isinstance(coord, (int, float)) for coord in point):
                            self._add_issue("INVALID_TYPE",
                                f"'{params_path}.points[{i}]' coordinates must be numbers.", element_id)

    def _check_fields(self, path: str, data: Dict, field_map: Dict[str, Any], element_id: Optional[str] = None):
        """Helper to check for required fields and their types."""
        for field, expected_type in field_map.items():
            if field not in data:
                self._add_issue("MISSING_REQUIRED_FIELD", f"Field '{field}' is missing.", element_id, path=path)
            elif not isinstance(data[field], expected_type):
                actual_type = type(data[field]).__name__
                # Handle tuple of types (e.g., (int, float))
                if isinstance(expected_type, tuple):
                    type_names = ' or '.join(t.__name__ for t in expected_type)
                else:
                    type_names = expected_type.__name__
                self._add_issue("INVALID_TYPE", f"Field '{path}.{field}' has type '{actual_type}', expected '{type_names}'.", element_id)

    def _is_nested_key_present(self, data: Dict, key_path: str) -> bool:
        """Check if a nested key (e.g., 'styles.size') exists."""
        keys = key_path.split('.')
        current = data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        return True

    def print_issues(self):
        """Prints all collected issues to the console."""
        if not self.issues:
            return

        print(f"\n[WARNING] Found {len(self.issues)} validation issue(s) in '{os.path.basename(self.filepath)}':\n")

        # Group issues by category
        grouped_issues = {}
        for issue in self.issues:
            if issue.category not in grouped_issues:
                grouped_issues[issue.category] = []
            grouped_issues[issue.category].append(issue)

        # Print Syntax Errors first, as they are blocking
        if "SYNTAX_ERROR" in grouped_issues:
            print("JSON Syntax Error:")
            for issue in grouped_issues["SYNTAX_ERROR"]:
                # The message from the validate method is already formatted
                print(f"  {issue.message}")
            print()
            # No need to print other issues if there's a syntax error
            return

        # Print "Required Fields Missing" section
        if "MISSING_REQUIRED_FIELD" in grouped_issues:
            print("Required Fields Missing:")
            for i, issue in enumerate(grouped_issues["MISSING_REQUIRED_FIELD"]):
                if issue.element_id:
                    field_name = issue.message.replace("Field '", "").replace("' is missing.", "")
                    parent_context = ""
                    if issue.path:
                        # Path is like "Element 'ID'.parent.child", extract "parent.child"
                        path_parts = issue.path.split('.')
                        if len(path_parts) > 1:
                            parent_context = f" from '{'.'.join(path_parts[1:])}'"

                    print(f"  {i + 1}. Id=\"{issue.element_id}\" - {field_name} field is missing{parent_context} in this element ID")
                else:
                    # Fallback for issues without an element_id (e.g., top-level missing fields)
                    print(f"  {i + 1}. {issue.message}")
            print() # Add a newline for spacing

        # Print other issues
        for category, issues in grouped_issues.items():
            if category not in ["SYNTAX_ERROR", "MISSING_REQUIRED_FIELD"]:
                print(f"{category.replace('_', ' ').title()}:")
                for i, issue in enumerate(issues):
                    print(f"  {i + 1}. {issue}")
                print() # Add a newline for spacing

        # Determine what message to show at the end
        has_invalid_schema = "INVALID_SCHEMA_TYPE" in grouped_issues
        has_other_errors = any(cat not in ["INVALID_SCHEMA_TYPE", "SYNTAX_ERROR"] for cat in grouped_issues)

        if has_invalid_schema and has_other_errors:
            # Both invalid schema and fixable errors
            fixable_categories = [cat.replace('_', ' ').title() for cat in grouped_issues.keys()
                                if cat not in ["INVALID_SCHEMA_TYPE", "SYNTAX_ERROR"]]
            print(f"\nFix the {', '.join(fixable_categories)} errors and re-run this script")
        elif has_other_errors:
            # Only fixable errors (no invalid schema)
            print("\nfix all these errors and re-run this script.")
        # If only INVALID_SCHEMA_TYPE, don't show re-run message


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Validate a video design JSON file against schema rules.')
    parser.add_argument('--scene', type=int, help='Scene index')
    parser.add_argument('--topic', help='Topic name')
    parser.add_argument('file_path', nargs='?', help='Design file path (alternative to --scene and --topic)')
    args = parser.parse_args()

    # Determine the file path
    if args.scene is not None and args.topic:
        # Sanitize topic name to prevent path traversal
        if '..' in args.topic or '/' in args.topic or '\\' in args.topic:
            print("Error: Invalid topic name. Topic cannot contain '..' or path separators.", file=sys.stderr)
            sys.exit(1)
        # Key-value pair mode: construct path from topic and scene
        file_path = os.path.join("Outputs", args.topic, "Design", "Latest", f"latest_{args.scene}.json")
    elif args.file_path:
        # Direct file path mode
        file_path = args.file_path
    else:
        print("Usage: python schema_validator.py --scene SCENE_INDEX --topic TOPIC", file=sys.stderr)
        print("       python schema_validator.py <design_file_path>", file=sys.stderr)
        sys.exit(1)

    if not file_path.lower().endswith('.json'):
        print(f"Error: The provided file '{file_path}' is not a .json file.", file=sys.stderr)
        sys.exit(1)

    validator = SchemaValidator(file_path)
    validator.validate()

if __name__ == "__main__":
    main()
