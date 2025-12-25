#!/usr/bin/env python3
"""
Token Counter Script
Counts tokens in files using tiktoken and prints results to terminal.

Usage:
    python scripts/token_counter.py file1.txt file2.py
    python scripts/token_counter.py "src/**/*.py"
    python scripts/token_counter.py *.md --model gpt-4
"""

import argparse
import glob
import os

try:
    import tiktoken
except ImportError:
    print("Error: tiktoken not installed. Run: pip install tiktoken")
    exit(1)


def count_tokens(text: str, encoding) -> int:
    """Count tokens in text using the provided encoding."""
    return len(encoding.encode(text))


def read_file(file_path: str) -> str | None:
    """Read file content with multiple encoding fallbacks."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception:
            return None

    return None


def expand_file_patterns(patterns: list[str]) -> list[str]:
    """Expand glob patterns to actual file paths."""
    files = []
    for pattern in patterns:
        if '*' in pattern or '?' in pattern:
            matched = glob.glob(pattern, recursive=True)
            files.extend(matched)
        elif os.path.isfile(pattern):
            files.append(pattern)
        elif os.path.isdir(pattern):
            for root, _, filenames in os.walk(pattern):
                for filename in filenames:
                    files.append(os.path.join(root, filename))

    seen = set()
    unique_files = []
    for f in files:
        normalized = os.path.normpath(f)
        if normalized not in seen:
            seen.add(normalized)
            unique_files.append(normalized)

    return unique_files


def main():
    parser = argparse.ArgumentParser(
        description="Count tokens in files using tiktoken",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python token_counter.py file.txt
    python token_counter.py *.py
    python token_counter.py "src/**/*.ts" --model gpt-4
        """
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="File paths or glob patterns (e.g., *.py, src/**/*.ts)"
    )

    parser.add_argument(
        "-m", "--model",
        default="gpt-4",
        help="Model to use for tokenization (default: gpt-4)"
    )

    args = parser.parse_args()

    # Expand file patterns
    files = expand_file_patterns(args.files)

    if not files:
        print("No files found matching the provided patterns.")
        return 1

    # Get encoding for the specified model
    try:
        encoding = tiktoken.encoding_for_model(args.model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # Calculate column widths
    max_filename_len = max(len(f) for f in files)
    max_filename_len = max(max_filename_len, len("File Name"))

    # Print header
    print()
    print(f"{'File Name':<{max_filename_len}} | {'Token Count':>12} | {'Character Count':>15} | {'Word Count':>10}")
    print("-" * max_filename_len + "-+-" + "-" * 12 + "-+-" + "-" * 15 + "-+-" + "-" * 10)

    total_tokens = 0
    total_chars = 0
    total_words = 0

    for file_path in files:
        content = read_file(file_path)

        if content is None:
            print(f"{file_path:<{max_filename_len}} | {'ERROR':>12} | {'ERROR':>15} | {'ERROR':>10}")
            continue

        token_count = count_tokens(content, encoding)
        char_count = len(content)
        word_count = len(content.split())

        total_tokens += token_count
        total_chars += char_count
        total_words += word_count

        print(f"{file_path:<{max_filename_len}} | {token_count:>12,} | {char_count:>15,} | {word_count:>10,}")

    # Print totals
    if len(files) > 1:
        print("-" * max_filename_len + "-+-" + "-" * 12 + "-+-" + "-" * 15 + "-+-" + "-" * 10)
        print(f"{'TOTAL':<{max_filename_len}} | {total_tokens:>12,} | {total_chars:>15,} | {total_words:>10,}")

    print()
    return 0


if __name__ == "__main__":
    exit(main())
