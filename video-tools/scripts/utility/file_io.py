import json
from pathlib import Path
from scripts.logging_config import get_utility_logger

logger = get_utility_logger('utility.file_io')


def read_from_file(file_path: str) -> str | None:
    if not file_path:
        logger.warning("[FILE_IO] No file_path provided, skipping read")
        return None
    try:
        path = Path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"[FILE_IO] Successfully read from: {file_path} ({len(content)} chars)")
        return content
    except Exception as e:
        logger.error(f"[FILE_IO] Failed to read from {file_path}: {e}")
        return None


def write_to_file(file_path: str, content) -> bool:
    if not file_path:
        logger.warning("[FILE_IO] No file_path provided, skipping write")
        return False

    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            if isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f, indent=2, ensure_ascii=False)

        logger.info(f"[FILE_IO] Successfully wrote to: {file_path}")
        return True

    except Exception as e:
        logger.error(f"[FILE_IO] Failed to write to {file_path}: {e}")
        return False
