import sys
import json
import os
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
import re

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def read_stdin() -> Dict[str, Any]:
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:  # Add this check
            info_log(f"input_data: {input_data}", "stdin_empty.log")
            return {}
        json_data = json.loads(input_data)
        return json_data
    except Exception as e:
        error_message = f"Error in read_stdin: {str(e)}"
        error_traceback = traceback.format_exc()
        error_log(error_message, error_traceback, "hooks_error.log")

def ensure_directory(path: str) -> None:
    """Create directory if it doesn't exist."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        error_message = f"Error creating directory {path}: {str(e)}"
        error_traceback = traceback.format_exc()
        error_log(error_message, error_traceback, "directory_error.log")

def read_json(filepath: str) -> Optional[Dict[str, Any]]:
    """Read JSON data from a file."""
    try:
        # Normalize the file path to handle backslashes properly
        normalized_path = os.path.normpath(filepath)
        with open(normalized_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        error_message = f"Error reading JSON from {filepath}: {str(e)}"
        error_traceback = traceback.format_exc()
        error_log(error_message, error_traceback, "read_json_error.log")
        return None

def read_jsonl(filepath: str) -> Optional[list]:
    """Read JSONL (JSON Lines) data from a file and return as array of objects."""
    try:
        # Normalize the file path to handle backslashes properly
        normalized_path = os.path.normpath(filepath)
        objects = []
        with open(normalized_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    objects.append(json.loads(line))
        return objects
    except Exception as e:
        error_message = f"Error reading JSONL from {filepath}: {str(e)}"
        error_traceback = traceback.format_exc()
        error_log(error_message, error_traceback, "read_jsonl_error.log")
        return None

def write_json(filepath: str, data: Dict[str, Any]) -> bool:
    """Write JSON data to a file."""
    try:
        # Ensure the directory exists before writing
        directory = os.path.dirname(filepath)
        if directory:
            ensure_directory(directory)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        error_message = f"Error writing JSON to {filepath}: {str(e)}"
        error_traceback = traceback.format_exc()
        error_log(error_message, error_traceback, "write_json_error.log")
        return False

def error_log(error_message: str, error_traceback: str, file_name: str="hooks_error.log") -> None:
    try:
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "traceback": error_traceback
        }
        ensure_directory("Outputs/hooks_logs")

        with open("Outputs/hooks_logs/" + file_name, "w", encoding="utf-8") as f:
            import json
            json.dump(error_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        error_message = f"Error in error_log: {str(e)}"
        error_traceback = traceback.format_exc()
        error_log(error_message, error_traceback, "hooks_error_error.log")

def info_log(info_message: Any, file_name: str="hooks_info.log") -> None:
    try:
        info_data = {
            "timestamp": datetime.now().isoformat(),
            "info": info_message
        }
        ensure_directory("Outputs/hooks_logs")
        with open("Outputs/hooks_logs/" + file_name, "w", encoding="utf-8") as f:
            if isinstance(info_message, dict):
                json.dump(info_data, f, indent=2, ensure_ascii=False)
            else:
                f.write(str(info_message))
    except Exception as e:
        error_message = f"Error in info_log: {str(e)}"
        error_traceback = traceback.format_exc()
        error_log(error_message, error_traceback, "hooks_info_error.log")

class BaseHook(ABC):
    def __init__(
        self,
        input_data: Dict[str, Any],
        hook_name: str,
        logs_dir: str = r"Outputs\hooks_logs",
        agents:List[str] = [],
    ):
        self.hook_name = hook_name
        self.logs_dir = logs_dir
        self.hook_data = input_data
        self.agents = agents
        self.log_file_path = f"{self.hook_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        self.log_file_path = os.path.join(self.logs_dir, self.log_file_path)
        ensure_directory(str(self.logs_dir))

    def error_log(self, error_message: str, error_traceback: str) -> None:
        error_data = {
            "hook_name": self.hook_name,
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "traceback": error_traceback
        }
        write_json(str(self.logs_dir / f"{self.hook_name}_error.log"), error_data)

    def process_transcripts(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            data = {**json_data}
            if data.get("agent_transcript_path"):
                result = read_jsonl(data["agent_transcript_path"])
                if result:
                    data["agent_transcript_data"] = result

            # if data.get("transcript_path"):
            #     result = read_jsonl(json_data["transcript_path"])
            #     if result:
            #         data["transcript_data"] = result
            return data

        except Exception as e:
            error_message = f"Error in process_transcripts: {str(e)}"
            error_traceback = traceback.format_exc()
            self.error_log(error_message, error_traceback)
            return {}

    def extract_value(self, entry: Dict[str, Any], path: str) -> Any:
        """
        Extract value from nested dict using dot notation.
        Supports array wildcard notation like 'content[*].name' to search in arrays.

        Args:
            entry: The dictionary to extract from
            path: Dot-separated path like "toolUseResult.filePath" or "message.content[*].name"

        Returns:
            Value at path, or None if not found.
            For array wildcards, returns first matching value found.
        """
        try:
            if not entry or not path:
                return None

            parts = path.split(".")
            current = entry

            for part in parts:
                if current is None:
                    return None

                # Handle array wildcard notation like "content[*]"
                if "[*]" in part:
                    key = part.replace("[*]", "")
                    if not isinstance(current, dict) or key not in current:
                        return None

                    array_val = current.get(key)
                    if not isinstance(array_val, list):
                        return None

                    # Get remaining path after this part
                    remaining_idx = parts.index(part) + 1
                    remaining_path = ".".join(parts[remaining_idx:]) if remaining_idx < len(parts) else ""

                    # Search through array items
                    for item in array_val:
                        if remaining_path:
                            result = self.extract_value(item, remaining_path)
                            if result is not None:
                                return result
                        else:
                            return item
                    return None

                # Standard dict access
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

            return current
        except Exception as e:
            error_message = f"Error in extract_value: {str(e)}"
            error_traceback = traceback.format_exc()
            self.error_log(error_message, error_traceback)
            return None

    def extract_all_values(self, entry: Dict[str, Any], path: str) -> List[Any]:
        """
        Extract all values from nested dict using dot notation.
        Similar to extract_value but returns ALL matches for array wildcards.

        Args:
            entry: The dictionary to extract from
            path: Dot-separated path like "message.content[*].name"

        Returns:
            List of all values found at path.
        """
        if not entry or not path:
            return []

        parts = path.split(".")
        results = []

        def traverse(current: Any, part_idx: int) -> None:
            if current is None or part_idx >= len(parts):
                if part_idx >= len(parts) and current is not None:
                    results.append(current)
                return

            part = parts[part_idx]

            # Handle array wildcard
            if "[*]" in part:
                key = part.replace("[*]", "")
                if isinstance(current, dict) and key in current:
                    array_val = current.get(key)
                    if isinstance(array_val, list):
                        for item in array_val:
                            traverse(item, part_idx + 1)
            elif isinstance(current, dict):
                traverse(current.get(part), part_idx + 1)

        traverse(entry, 0)
        return results

    def evaluate_condition(self, entry: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """
        Evaluate a single condition against an entry.

        Supported conditions:
        - {"and": [...]} - all must match
        - {"or": [...]} - at least one must match
        - {"not": {...}} - negates the condition
        - {"exists": "path"} - field exists and is not None
        - {"eq": {"field": "path", "value": X}} - equals
        - {"neq": {"field": "path", "value": X}} - not equals
        - {"startswith": {"field": "path", "value": X}} - string starts with
        - {"endswith": {"field": "path", "value": X}} - string ends with
        - {"contains": {"field": "path", "value": X}} - string contains
        - {"match": {"field": "path", "pattern": X}} - regex match
        - {"in": {"field": "path", "values": [...]}} - value in list

        Args:
            entry: The transcript entry to evaluate
            condition: The condition object

        Returns:
            True if condition matches, False otherwise
        """
        if not condition or not isinstance(condition, dict):
            return False

        # AND condition
        if "and" in condition:
            conditions = condition["and"]
            if not isinstance(conditions, list):
                return False
            return all(self.evaluate_condition(entry, c) for c in conditions)

        # OR condition
        if "or" in condition:
            conditions = condition["or"]
            if not isinstance(conditions, list):
                return False
            return any(self.evaluate_condition(entry, c) for c in conditions)

        # NOT condition
        if "not" in condition:
            return not self.evaluate_condition(entry, condition["not"])

        # EXISTS condition
        if "exists" in condition:
            path = condition["exists"]
            value = self.extract_value(entry, path)
            return value is not None

        # EQ condition
        if "eq" in condition:
            params = condition["eq"]
            field = params.get("field")
            expected = params.get("value")
            # Support array wildcards - check if any value matches
            values = self.extract_all_values(entry, field)
            if not values:
                actual = self.extract_value(entry, field)
                return actual == expected
            return any(v == expected for v in values)

        # NEQ condition
        if "neq" in condition:
            params = condition["neq"]
            field = params.get("field")
            expected = params.get("value")
            actual = self.extract_value(entry, field)
            return actual != expected

        # STARTSWITH condition
        if "startswith" in condition:
            params = condition["startswith"]
            field = params.get("field")
            prefix = params.get("value", "")
            values = self.extract_all_values(entry, field)
            if not values:
                actual = self.extract_value(entry, field)
                return isinstance(actual, str) and actual.startswith(prefix)
            return any(isinstance(v, str) and v.startswith(prefix) for v in values)

        # ENDSWITH condition
        if "endswith" in condition:
            params = condition["endswith"]
            field = params.get("field")
            suffix = params.get("value", "")
            values = self.extract_all_values(entry, field)
            if not values:
                actual = self.extract_value(entry, field)
                return isinstance(actual, str) and actual.endswith(suffix)
            return any(isinstance(v, str) and v.endswith(suffix) for v in values)

        # CONTAINS condition
        if "contains" in condition:
            params = condition["contains"]
            field = params.get("field")
            substring = params.get("value", "")
            values = self.extract_all_values(entry, field)
            if not values:
                actual = self.extract_value(entry, field)
                return isinstance(actual, str) and substring in actual
            return any(isinstance(v, str) and substring in v for v in values)

        # MATCH condition (regex)
        if "match" in condition:
            params = condition["match"]
            field = params.get("field")
            pattern = params.get("pattern", "")
            values = self.extract_all_values(entry, field)
            if not values:
                actual = self.extract_value(entry, field)
                if not isinstance(actual, str):
                    return False
                try:
                    return bool(re.search(pattern, actual))
                except re.error:
                    return False
            for v in values:
                if isinstance(v, str):
                    try:
                        if re.search(pattern, v):
                            return True
                    except re.error:
                        pass
            return False

        # IN condition
        if "in" in condition:
            params = condition["in"]
            field = params.get("field")
            allowed = params.get("values", [])
            values = self.extract_all_values(entry, field)
            if not values:
                actual = self.extract_value(entry, field)
                return actual in allowed
            return any(v in allowed for v in values)

        return False

    def match_transcript(
        self,
        query: Dict[str, Any],
        return_field: str = None
    ) -> Tuple[bool, Any]:
        try:
            data = self.hook_data.get("input", {})
            transcript_data = data.get("agent_transcript_data", [])

            for entry in transcript_data:
                if not isinstance(entry, dict):
                    continue

                if self.evaluate_condition(entry, query):
                    if return_field:
                        return True, self.extract_value(entry, return_field)
                    return True, entry

            return False, None
        except Exception as e:
            error_message = f"Error in match_transcript: {str(e)}"
            error_traceback = traceback.format_exc()
            self.error_log(error_message, error_traceback)
            return False, None

    def match_transcript_all(
        self,
        query: Dict[str, Any],
        return_field: str = None
    ) -> List[Tuple[bool, Any]]:
        """
        Find all entries in agent_transcript_data matching the query.

        Args:
            query: Query object with conditions
            return_field: Optional dot-path of field to return

        Returns:
            List of (True, value) tuples for each matching entry
        """
        data = self.hook_data.get("input", {})
        transcript_data = data.get("agent_transcript_data", [])
        results = []

        for entry in transcript_data:
            if not isinstance(entry, dict):
                continue

            if self.evaluate_condition(entry, query):
                if return_field:
                    results.append((True, self.extract_value(entry, return_field)))
                else:
                    results.append((True, entry))

        return results

    @abstractmethod
    def should_run_hook(self) -> bool:
        pass

    def save_log(self, data: Dict[str, Any], suffix: str = "") -> str:
        try:
            output_file_path = self.log_file_path
            write_json(output_file_path, data)
            return output_file_path
        except Exception as e:
            error_message = f"Error in save_log: {str(e)}"
            error_traceback = traceback.format_exc()
            self.error_log(error_message, error_traceback)
            return ""

    def prepare_output_data(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return {
                "hook_name": self.hook_name,
                "timestamp": datetime.now().isoformat(),
                "input": json_data
            }
        except Exception as e:
            error_message = f"Error in prepare_output_data: {str(e)}"
            error_traceback = traceback.format_exc()
            self.error_log(error_message, error_traceback)
            return {}

    def process_hook_data(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            data=self.process_transcripts(json_data)
            self.hook_data = data
            return data
        except Exception as e:
            error_message = f"Error in process_hook_data: {str(e)}"
            error_traceback = traceback.format_exc()
            self.error_log(error_message, error_traceback)
            return {}

    @abstractmethod
    def set_log_path(self) -> None:
        """Set the log file path. Must be implemented by subclasses."""
        pass

    def run(self) -> None:
        try:
            self.hook_data = self.process_hook_data(self.hook_data)
            self.hook_data = self.prepare_output_data(self.hook_data)
            self.set_log_path()
            self.save_log(self.hook_data)
            return self.should_run_hook()
        except Exception as e:
            error_message = f"Error in run: {str(e)}"
            error_traceback = traceback.format_exc()
            self.error_log(error_message, error_traceback)
