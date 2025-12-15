#!/usr/bin/env python3

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from path_manager import PathManager


RED = '\033[91m'
RESET = '\033[0m'


def get_line_context(content: str, error_position: int, context_lines: int = 2):
    lines = content.split('\n')
    current_pos = 0
    line_number = 0
    column = 0

    for i, line in enumerate(lines):
        line_length = len(line) + 1
        if current_pos + line_length > error_position:
            line_number = i + 1
            column = error_position - current_pos + 1
            break
        current_pos += line_length

    start_line = max(0, line_number - 1 - context_lines)
    end_line = min(len(lines), line_number + context_lines)
    context = lines[start_line:end_line]

    return {
        'line_number': line_number,
        'column': column,
        'context': context,
        'error_line_index': line_number - 1 - start_line,
        'start_line': start_line + 1
    }


def print_error_context(context_info):
    print(f"\nContext:")
    for i, line in enumerate(context_info['context']):
        line_num = context_info['start_line'] + i
        is_error_line = i == context_info['error_line_index']

        line_num_str = f"{line_num:4d} │ "

        if is_error_line:
            print(f"{RED}{line_num_str}{line}{RESET}")
            pointer_padding = len(line_num_str) + context_info['column'] - 1
            pointer = ' ' * pointer_padding + f"{RED}^{RESET}"
            print(pointer)
        else:
            print(f"{line_num_str}{line}")


def validate_json_file(file_path: str):
    path = Path(file_path)

    if not path.exists():
        print(f"{RED}File not found: {file_path}{RESET}")
        return False

    if not path.is_file():
        print(f"{RED}Path is not a file: {file_path}{RESET}")
        return False

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            print(f"{RED}File is empty{RESET}")
            return False

        json.loads(content)

        print(f"JSON is valid: {file_path}")
        return True

    except json.JSONDecodeError as e:
        print(f"{RED}JSON is invalid: {file_path}{RESET}")
        print(f"\n{RED}Error: {e.msg}{RESET}")
        print(f"Line: {e.lineno}, Column: {e.colno}")

        try:
            context_info = get_line_context(content, e.pos)
            print_error_context(context_info)
        except Exception:
            pass

        return False

    except UnicodeDecodeError as e:
        print(f"{RED}File encoding error: {e}{RESET}")
        return False

    except Exception as e:
        print(f"{RED}Unexpected error: {e}{RESET}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Validate JSON file format')
    parser.add_argument('--topic', required=True, help='Topic name')
    parser.add_argument('--asset-type', required=True, help='Asset type (Design, Direction, Video, etc.)')
    parser.add_argument('--scene-index', type=int, help='Scene index (required for Design and Video)')

    args = parser.parse_args()

    try:
        manager = PathManager(topic=args.topic)
        file_path = manager.get_path(args.asset_type, args.scene_index, subpath='latest')

        success = validate_json_file(file_path)
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
