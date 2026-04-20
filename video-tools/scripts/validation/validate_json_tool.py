import json
import time
from datetime import datetime

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('tools.validate_json_tool')


def validate_json(json_content: str) -> dict:
    func_start = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    logger.debug(f"[VALIDATE_JSON] >>> FUNCTION ENTRY at {timestamp}")
    logger.debug(f"[VALIDATE_JSON] Input json_content type: {type(json_content).__name__}")
    logger.debug(f"[VALIDATE_JSON] Input json_content length: {len(json_content) if json_content else 0} chars")

    if json_content:
        logger.debug(f"[VALIDATE_JSON] Content preview: '{json_content[:500]}{'...' if len(json_content) > 500 else ''}'")

    logger.debug(f"[VALIDATE_JSON] Step 1: Checking for empty content...")
    if not json_content or not json_content.strip():
        func_elapsed = time.time() - func_start
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        logger.debug(f"[VALIDATE_JSON] Content is empty or whitespace only")
        logger.debug(f"[VALIDATE_JSON] Returning: success=False, error='JSON content is empty'")
        logger.debug(f"[VALIDATE_JSON] Total function time: {func_elapsed*1000:.2f}ms")
        logger.debug(f"[VALIDATE_JSON] <<< FUNCTION EXIT at {end_timestamp}")
        return {"success": False, "errors": [{"message": "JSON content is empty"}]}

    logger.debug(f"[VALIDATE_JSON] Step 2: Attempting json.loads()...")
    parse_start = time.time()

    try:
        parsed = json.loads(json_content)
        parse_elapsed = time.time() - parse_start
        func_elapsed = time.time() - func_start
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        logger.debug(f"[VALIDATE_JSON] json.loads() succeeded in {parse_elapsed*1000:.2f}ms")
        logger.debug(f"[VALIDATE_JSON] Parsed type: {type(parsed).__name__}")
        if isinstance(parsed, dict):
            logger.debug(f"[VALIDATE_JSON] Parsed dict keys: {list(parsed.keys())[:10]}{'...' if len(parsed.keys()) > 10 else ''}")
        elif isinstance(parsed, list):
            logger.debug(f"[VALIDATE_JSON] Parsed list length: {len(parsed)}")
        logger.debug(f"[VALIDATE_JSON] Returning: success=True, errors=[]")
        logger.debug(f"[VALIDATE_JSON] Total function time: {func_elapsed*1000:.2f}ms")
        logger.debug(f"[VALIDATE_JSON] <<< FUNCTION EXIT at {end_timestamp}")
        return {"success": True, "errors": []}

    except json.JSONDecodeError as e:
        parse_elapsed = time.time() - parse_start
        func_elapsed = time.time() - func_start
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        logger.debug(f"[VALIDATE_JSON] json.loads() failed in {parse_elapsed*1000:.2f}ms")
        logger.debug(f"[VALIDATE_JSON] JSONDecodeError: {e.msg}")
        logger.debug(f"[VALIDATE_JSON] Error location: line {e.lineno}, column {e.colno}")
        logger.debug(f"[VALIDATE_JSON] Error position: char {e.pos}")

        # Show context around error
        if e.pos is not None and json_content:
            start_ctx = max(0, e.pos - 30)
            end_ctx = min(len(json_content), e.pos + 30)
            context = json_content[start_ctx:end_ctx]
            logger.debug(f"[VALIDATE_JSON] Error context: '...{context}...'")

        error_msg = f"{e.msg} at line {e.lineno}, column {e.colno}"
        logger.debug(f"[VALIDATE_JSON] Returning: success=False, error='{error_msg}'")
        logger.debug(f"[VALIDATE_JSON] Total function time: {func_elapsed*1000:.2f}ms")
        logger.debug(f"[VALIDATE_JSON] <<< FUNCTION EXIT at {end_timestamp}")
        return {"success": False, "errors": [{"message": error_msg}]}

    except Exception as e:
        parse_elapsed = time.time() - parse_start
        func_elapsed = time.time() - func_start
        end_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        logger.error(f"[VALIDATE_JSON] Unexpected error in {parse_elapsed*1000:.2f}ms")
        logger.error(f"[VALIDATE_JSON] Exception type: {type(e).__name__}")
        logger.error(f"[VALIDATE_JSON] Exception message: {str(e)}")
        logger.debug(f"[VALIDATE_JSON] Returning: success=False, error='{str(e)}'")
        logger.debug(f"[VALIDATE_JSON] Total function time: {func_elapsed*1000:.2f}ms")
        logger.debug(f"[VALIDATE_JSON] <<< FUNCTION EXIT at {end_timestamp}")
        return {"success": False, "errors": [{"message": str(e)}]}
