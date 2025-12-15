import os
import json
import re
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Union
from scripts.controllers.utils.decorators.try_catch import try_catch, try_catch_bool, try_catch_dict, try_catch_list, try_catch_none
from scripts.controllers.utils.singleton import SingletonMeta


class SystemIOController(metaclass=SingletonMeta):

    def __init__(self):
        self.encoding = 'utf-8'

    def _normalize_path(self, filepath: str) -> str:
        """
        Normalize path to work cross-platform.
        Converts forward/backward slashes to OS-appropriate separators.
        """
        # Replace Windows backslashes with forward slashes first
        # This ensures Path() can properly interpret the path on all platforms
        normalized = filepath.replace('\\', '/')
        return str(Path(normalized))

    def normalize_path(self, filepath: str) -> str:
        """
        Public method to normalize path for cross-platform compatibility.
        Converts Windows-style backslashes to forward slashes before creating Path object.
        """
        return self._normalize_path(filepath)

    def copy_file(self, source_path: str, destination_path: str) -> bool:
        source_path = self._normalize_path(source_path)
        destination_path = self._normalize_path(destination_path)
        if not self.exists(source_path):
            raise FileNotFoundError(f"File not found: {source_path}")
        shutil.copy(source_path, destination_path)
        return True

    @try_catch()
    def read_file(self, filepath: str, extension: Optional[str] = None) -> Union[Dict, str, bytes]:
        filepath = self._normalize_path(filepath)
        if not self.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        ext = extension or Path(filepath).suffix.lower()

        if ext == '.json':
            return self.read_json(filepath)
        elif ext in ['.mp3', '.wav', '.png', '.jpg', '.jpeg', '.gif', '.pdf']:
            return self.read_binary(filepath)
        else:
            return self.read_text(filepath)

    @try_catch_bool
    def write_file(self, filepath: str, content: Union[Dict, str, bytes], extension: Optional[str] = None) -> bool:
        filepath = self._normalize_path(filepath)
        self.ensure_directory(self.get_directory(filepath))

        ext = extension or Path(filepath).suffix.lower()

        if ext == '.json':
            if isinstance(content, dict) or isinstance(content, list):
                self.write_json(filepath, content)
            else:
                raise ValueError(f"Expected dict or list for JSON file, got {type(content)}")
        elif ext in ['.mp3', '.wav', '.png', '.jpg', '.jpeg', '.gif', '.pdf'] or isinstance(content, bytes):
            if not isinstance(content, bytes):
                raise ValueError(f"Expected bytes for binary file, got {type(content)}")
            self.write_binary(filepath, content)
        else:
            if not isinstance(content, str):
                content = str(content)
            self.write_text(filepath, content)
        return True

    @try_catch_dict
    def read_json(self, filepath: str,check_exists: bool = True) -> Dict:
        filepath = self._normalize_path(filepath)
        if not self.exists(filepath):
            if check_exists:
                raise FileNotFoundError(f"File not found: {filepath}")
            else:
                return None
        with open(filepath, 'r', encoding=self.encoding) as f:
            return json.load(f)

    @try_catch_bool
    def write_json(self, filepath: str, data: Union[Dict, List], indent: int = 2) -> bool:
        filepath = self._normalize_path(filepath)
        self.ensure_directory(self.get_directory(filepath))
        with open(filepath, 'w', encoding=self.encoding) as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True

    @try_catch(return_on_error="")
    def read_text(self, filepath: str) -> str:
        filepath = self._normalize_path(filepath)
        with open(filepath, 'r', encoding=self.encoding) as f:
            return f.read()

    @try_catch_bool
    def write_text(self, filepath: str, content: str) -> bool:
        filepath = self._normalize_path(filepath)
        self.ensure_directory(self.get_directory(filepath))
        with open(filepath, 'w', encoding=self.encoding) as f:
            f.write(content)
        return True

    @try_catch(return_on_error=b"")
    def read_binary(self, filepath: str) -> bytes:
        filepath = self._normalize_path(filepath)
        with open(filepath, 'rb') as f:
            return f.read()

    @try_catch_bool
    def write_binary(self, filepath: str, data: bytes) -> bool:
        filepath = self._normalize_path(filepath)
        self.ensure_directory(self.get_directory(filepath))
        with open(filepath, 'wb') as f:
            f.write(data)
        return True

    @try_catch_bool
    def delete_file(self, filepath: str) -> bool:
        filepath = self._normalize_path(filepath)
        if not self.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        os.remove(filepath)
        return True

    def exists(self, path: str) -> bool:
        path = self._normalize_path(path)
        return os.path.exists(path)

    @try_catch_bool
    def ensure_directory(self, directory_path: str) -> bool:
        if directory_path:
            directory_path = self._normalize_path(directory_path)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path, exist_ok=True)
        return True

    def get_directory(self, filepath: str) -> str:
        return os.path.dirname(filepath)

    @try_catch_list
    def list_directories(self, directory: str) -> List[str]:
        directory = self._normalize_path(directory)
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
        return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]

    @try_catch_list
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        directory = self._normalize_path(directory)
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")

        path = Path(directory)
        if pattern == "*":
            return [f.name for f in path.iterdir() if f.is_file()]
        else:
            return [f.name for f in path.glob(pattern) if f.is_file()]

    @try_catch(return_on_error=1)
    def get_next_version(self, directory: str, prefix: str, extension: str) -> int:
        directory = self._normalize_path(directory)
        if not os.path.exists(directory):
            return 1

        pattern = re.compile(f'^{re.escape(prefix)}-v(\\d+){re.escape(extension)}$')

        max_version = 0
        for filename in os.listdir(directory):
            match = pattern.match(filename)
            if match:
                version = int(match.group(1))
                max_version = max(max_version, version)

        return max_version + 1

    @try_catch_none
    def get_latest_file(self, directory: str, prefix: str, extension: str) -> Optional[str]:
        directory = self._normalize_path(directory)
        if not os.path.exists(directory):
            return None

        pattern = re.compile(f'^{re.escape(prefix)}-v(\\d+){re.escape(extension)}$')

        max_version = 0
        latest_file = None

        for filename in os.listdir(directory):
            match = pattern.match(filename)
            if match:
                version = int(match.group(1))
                if version > max_version:
                    max_version = version
                    latest_file = filename

        if latest_file:
            return os.path.join(directory, latest_file)
        return None


system_io = SystemIOController()