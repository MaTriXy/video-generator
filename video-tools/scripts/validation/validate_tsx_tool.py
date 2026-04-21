import ast
import asyncio
import json
import os
import re
import tempfile
import time
from pathlib import Path

from scripts.logging_config import get_utility_logger

logger = get_utility_logger('tools.validate_tsx_tool')

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

IGNORED_ERROR_CODES = {
    "TS2307",
    "TS2306",
    "TS2792",
    "TS2305",
    "TS2614",
}

# Semaphore to limit concurrent TSC processes (max 10)
# Initialized once at module load - no race condition possible
_tsc_semaphore = asyncio.Semaphore(10)

# Semaphore for Remotion runtime validation (esbuild + Node.js, lightweight)
_remotion_semaphore = asyncio.Semaphore(10)

# Remotion project path and validator script
REMOTION_PROJECT_DIR = os.getenv('REMOTION_PROJECT_DIR', str(ROOT_DIR))
REMOTION_VALIDATOR_SCRIPT = ROOT_DIR / "scripts" / "validation" / "remotion_render_validator.mjs"


def parse_tsc_errors(output: str) -> list[dict]:
    errors = []
    pattern = r'([^(]+)\((\d+),(\d+)\):\s*(error|warning)\s+(TS\d+):\s*(.+)'

    for match in re.finditer(pattern, output):
        error_code = match.group(5)
        if error_code in IGNORED_ERROR_CODES:
            continue

        errors.append({
            "file": match.group(1).strip(),
            "line": int(match.group(2)),
            "column": int(match.group(3)),
            "severity": match.group(4).upper(),
            "code": error_code,
            "message": match.group(6).strip()
        })

    return errors


def format_errors(errors: list[dict]) -> str:
    if not errors:
        return "No errors found."

    output_lines = []
    for error in errors:
        output_lines.append(
            f"  [{error['severity']}] Line {error['line']}:{error['column']} - {error['message']}"
        )
        output_lines.append(f"           Code: {error['code']}")

    return "\n".join(output_lines)


# ---------------------------------------------------------------------------
# Static analysis: typing prop inputRange validation
# ---------------------------------------------------------------------------
# The Text component (injected as a prop) calls:
#   interpolate(frame, [typing.startFrame, typing.endFrame], [0, 1], ...)
# Remotion requires inputRange to be strictly monotonically increasing.
# The runtime validator misses this because it calls SceneComponent({}) with
# no props, so Text is undefined and the interpolate call never executes.
# These functions statically check that startFrame < endFrame in all branches.


def _safe_eval_arithmetic(expr_str: str):
    """Safely evaluate a pure arithmetic expression (numbers with +, -, *, /).
    Returns float if evaluable, None otherwise."""
    expr_str = expr_str.strip()
    if not expr_str:
        return None
    try:
        tree = ast.parse(expr_str, mode='eval')
    except SyntaxError:
        return None

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            val = _eval_node(node.operand)
            return -val if val is not None else None
        if isinstance(node, ast.BinOp):
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if left is None or right is None:
                return None
            ops = {ast.Add: float.__add__, ast.Sub: float.__sub__,
                   ast.Mult: float.__mul__}
            op_func = ops.get(type(node.op))
            if op_func:
                return op_func(left, right)
            if isinstance(node.op, ast.Div) and right != 0:
                return left / right
        return None  # Name, Call, etc. — not evaluable

    return _eval_node(tree)


def _split_ternary(expr: str):
    """Split 'cond ? consequent : alternate' at top level.
    Skips ?. (optional chaining) and ?? (nullish coalescing).
    Returns (cond, consequent, alternate) or None."""
    depth_p = depth_b = depth_k = 0  # parens, braces, brackets
    q_pos = -1

    i = 0
    while i < len(expr):
        c = expr[i]
        if c == '(':  depth_p += 1
        elif c == ')': depth_p -= 1
        elif c == '{': depth_b += 1
        elif c == '}': depth_b -= 1
        elif c == '[': depth_k += 1
        elif c == ']': depth_k -= 1
        elif c == '?' and depth_p == 0 and depth_b == 0 and depth_k == 0:
            if i + 1 < len(expr) and expr[i + 1] in '.?':
                i += 2
                continue
            q_pos = i
            break
        i += 1

    if q_pos == -1:
        return None

    # Find matching ':' after '?'
    ternary_depth = 1
    depth_p = depth_b = depth_k = 0
    j = q_pos + 1
    colon_pos = -1
    while j < len(expr):
        c = expr[j]
        if c == '(':  depth_p += 1
        elif c == ')': depth_p -= 1
        elif c == '{': depth_b += 1
        elif c == '}': depth_b -= 1
        elif c == '[': depth_k += 1
        elif c == ']': depth_k -= 1
        elif c == '?' and depth_p == 0 and depth_b == 0 and depth_k == 0:
            if j + 1 < len(expr) and expr[j + 1] in '.?':
                j += 2
                continue
            ternary_depth += 1
        elif c == ':' and depth_p == 0 and depth_b == 0 and depth_k == 0:
            ternary_depth -= 1
            if ternary_depth == 0:
                colon_pos = j
                break
        j += 1

    if colon_pos == -1:
        return None

    return (expr[:q_pos].strip(),
            expr[q_pos + 1:colon_pos].strip(),
            expr[colon_pos + 1:].strip())


def _evaluate_branches(expr: str) -> list[float]:
    """Extract all possible numeric values from a JS expression.
    Handles ternary (cond ? A : B) by evaluating both branches recursively.
    Returns list of float values; empty if expression can't be evaluated."""
    ternary = _split_ternary(expr)
    if ternary is not None:
        _, consequent, alternate = ternary
        return _evaluate_branches(consequent) + _evaluate_branches(alternate)

    val = _safe_eval_arithmetic(expr)
    return [val] if val is not None else []


def _extract_typing_blocks(tsx_content: str) -> list[tuple[int, str]]:
    """Find all typing={{ ... }} blocks. Returns (line_number, inner_content) pairs."""
    results = []
    pattern = re.compile(r'typing=\{\{')
    for match in pattern.finditer(tsx_content):
        start_pos = match.end()
        depth = 2  # consumed '{{'
        i = start_pos
        in_string = None
        while i < len(tsx_content) and depth > 0:
            c = tsx_content[i]
            if in_string:
                if c == '\\':
                    i += 2
                    continue
                if c == in_string:
                    in_string = None
            elif c in ('"', "'", '`'):
                in_string = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            i += 1

        if depth == 0:
            inner = tsx_content[start_pos:i - 2]
            line_num = tsx_content[:match.start()].count('\n') + 1
            results.append((line_num, inner))
    return results


def _extract_field(block: str, field_name: str) -> str | None:
    """Extract the value expression for a field (e.g. 'startFrame: <expr>') from a typing block."""
    match = re.search(rf'\b{field_name}\s*:\s*', block)
    if not match:
        return None

    start = match.end()
    depth_p = depth_b = depth_k = 0
    in_string = None
    i = start
    while i < len(block):
        c = block[i]
        if in_string:
            if c == '\\':
                i += 2
                continue
            if c == in_string:
                in_string = None
        elif c in ('"', "'", '`'):
            in_string = c
        elif c == '(':  depth_p += 1
        elif c == ')':  depth_p -= 1
        elif c == '{':  depth_b += 1
        elif c == '}':  depth_b -= 1
        elif c == '[':  depth_k += 1
        elif c == ']':  depth_k -= 1
        elif c == ',' and depth_p == 0 and depth_b == 0 and depth_k == 0:
            break
        i += 1

    return block[start:i].strip()


def check_typing_props(tsx_content: str) -> list[dict]:
    """Static analysis: verify typing={{ startFrame, endFrame }} props always
    produce startFrame < endFrame (monotonically increasing inputRange).
    Returns list of error dicts compatible with the validation pipeline."""
    errors = []
    for line_num, block in _extract_typing_blocks(tsx_content):
        start_expr = _extract_field(block, 'startFrame')
        end_expr = _extract_field(block, 'endFrame')
        if not start_expr or not end_expr:
            continue

        start_values = _evaluate_branches(start_expr)
        end_values = _evaluate_branches(end_expr)

        for sv in start_values:
            for ev in end_values:
                if sv >= ev:
                    errors.append({
                        "severity": "ERROR",
                        "code": "TYPING_RANGE",
                        "message": (
                            f"Line {line_num}: typing prop has startFrame ({int(sv)}) >= "
                            f"endFrame ({int(ev)}) in some branch — this creates "
                            f"inputRange [{int(sv)}, {int(ev)}] which is not monotonically "
                            f"increasing and will crash interpolate() at runtime. "
                            f"Ensure startFrame < endFrame in ALL conditional branches. "
                            f"(startFrame: {start_expr}, endFrame: {end_expr})"
                        ),
                    })
                    return errors  # one error per block is enough
    return errors


async def validate_tsx_batch(components: list[dict], total_frames: int = 600) -> list[dict]:
    """
    Validate multiple TSX components concurrently.
    Each component dict must have 'tsx_content' and 'output_path' keys.
    Max 10 components. Returns a list of result dicts with 'output_path', 'success', 'errors', and 'message'.
    """
    func_start = time.time()
    logger.info(f"[VALIDATE_TSX] Batch request: {len(components)} components")

    if len(components) > 10:
        components = components[:10]
        logger.warning(f"[VALIDATE_TSX] Truncated batch to 10 components")

    async def validate_one(component: dict) -> dict:
        tsx_content = component.get("tsx_content", "")
        output_path = component.get("output_path", "")
        try:
            result = await validate_tsx(tsx_content, total_frames)
            if result.get("success") and output_path:
                try:
                    from scripts.utility.file_io import write_to_file
                    written = write_to_file(output_path, tsx_content)
                    if not written:
                        logger.warning(f"[VALIDATE_TSX] Validation passed but file write failed: {output_path}")
                        result["message"] = f"[PASSED] TSX validation passed but file write failed: {output_path}"
                except Exception as write_err:
                    logger.error(f"[VALIDATE_TSX] Validation passed but file write error: {type(write_err).__name__}: {write_err}")
                    result["message"] = f"[PASSED] TSX validation passed but file write error: {write_err}"
            return {
                "output_path": output_path,
                "success": result.get("success", False),
                "errors": result.get("errors", []),
                "message": result.get("message", ""),
            }
        except Exception as e:
            logger.error(f"[VALIDATE_TSX] Component failed unexpectedly: {type(e).__name__}: {e}")
            return {
                "output_path": output_path,
                "success": False,
                "errors": [],
                "message": f"Validation failed: {str(e)}",
            }

    results = await asyncio.gather(*[validate_one(c) for c in components])

    elapsed = time.time() - func_start
    passed = sum(1 for r in results if r["success"])
    logger.info(f"[VALIDATE_TSX] Batch complete: {passed}/{len(results)} passed in {elapsed*1000:.2f}ms")

    return list(results)


async def run_remotion_render_validation(temp_tsx_path: str, total_frames: int = 600) -> dict:
    """
    Run Remotion runtime validation by executing the component for every frame.
    Uses esbuild + mocked hooks + real interpolate/spring (no Chromium needed).
    Catches runtime errors like non-monotonic inputRange in interpolate().
    Returns {"success": True, "framesChecked": N} or {"success": False, "error": "...", "frame": N}.
    """
    cmd = [
        "node",
        str(REMOTION_VALIDATOR_SCRIPT),
        temp_tsx_path,
        REMOTION_PROJECT_DIR,
        str(total_frames),
    ]

    logger.info(f"[VALIDATE_TSX] Starting Remotion runtime validation...")
    logger.info(f"[VALIDATE_TSX] Remotion cmd: {' '.join(cmd)}")

    async with _remotion_semaphore:
        render_start = time.time()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error(f"[VALIDATE_TSX] Remotion runtime validation timed out after 30s")
            return {"success": False, "error": "Remotion runtime validation timed out after 30 seconds"}

        elapsed = time.time() - render_start
        logger.info(f"[VALIDATE_TSX] Remotion render: {elapsed*1000:.2f}ms, returncode={proc.returncode}")

    stdout_str = stdout_bytes.decode('utf-8').strip() if stdout_bytes else ''
    stderr_str = stderr_bytes.decode('utf-8').strip() if stderr_bytes else ''

    if stderr_str:
        logger.debug(f"[VALIDATE_TSX] Remotion stderr: {stderr_str[:500]}")

    if not stdout_str:
        return {"success": False, "error": f"Remotion validator produced no output. stderr: {stderr_str[:500]}"}

    try:
        result = json.loads(stdout_str)
        return result
    except json.JSONDecodeError:
        return {"success": False, "error": f"Remotion validator output parse error: {stdout_str[:500]}"}


async def validate_tsx(tsx_content: str, total_frames: int = 600) -> dict:
    """
    Async version of validate_tsx that doesn't block the event loop.
    Uses a semaphore to limit concurrent TSC processes to 10.
    After TSC passes, runs Remotion runtime validation for all frames.
    """
    func_start = time.time()
    temp_file = None  # Initialize to avoid UnboundLocalError in finally block

    logger.info(f"[VALIDATE_TSX] Request: {len(tsx_content) if tsx_content else 0} chars")

    # Check for empty content
    if not tsx_content or not tsx_content.strip():
        logger.info(f"[VALIDATE_TSX] Complete: empty content in {(time.time() - func_start)*1000:.2f}ms")
        return {"success": False, "errors": [], "message": "TSX content is empty"}

    # Locate TypeScript compiler (hoisted to monorepo root)
    monorepo_root = ROOT_DIR.parent.parent
    tsc_path = monorepo_root / "node_modules" / ".bin" / "tsc"
    if os.name == 'nt':
        tsc_path = monorepo_root / "node_modules" / ".bin" / "tsc.cmd"

    if not tsc_path.exists():
        logger.error(f"[VALIDATE_TSX] TypeScript compiler not found at {tsc_path}")
        return {
            "success": False,
            "errors": [],
            "message": "TypeScript compiler not found. Run: npm install typescript"
        }

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False, encoding='utf-8', dir=str(ROOT_DIR)) as f:
        f.write(tsx_content)
        temp_file = f.name
    logger.debug(f"[VALIDATE_TSX] Temp file created: {temp_file}")

    try:
        # Build command
        cmd = [
            str(tsc_path),
            "--noEmit",
            "--jsx", "react-jsx",
            "--esModuleInterop",
            "--skipLibCheck",
            "--lib", "es2020,dom",
            temp_file
        ]
        logger.debug(f"[VALIDATE_TSX] Command: {' '.join(cmd)}")

        # Run TSC with semaphore (max 5 concurrent)
        async with _tsc_semaphore:
            subprocess_start = time.time()

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(ROOT_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error(f"[VALIDATE_TSX] TSC timed out after 30s, killing process")
                proc.kill()
                await proc.wait()
                return {"success": False, "errors": [], "message": "TSC validation timed out after 30 seconds"}

            logger.debug(f"[VALIDATE_TSX] TSC subprocess: {(time.time() - subprocess_start)*1000:.2f}ms, returncode={proc.returncode}")

        # Decode output
        stdout = stdout_bytes.decode('utf-8') if stdout_bytes else ''
        stderr = stderr_bytes.decode('utf-8') if stderr_bytes else ''
        returncode = proc.returncode

        logger.debug(f"[VALIDATE_TSX] returncode={returncode}, stdout={len(stdout)} chars, stderr={len(stderr)} chars")

        # TSC passed - now run Remotion runtime validation
        if returncode == 0:
            # Static analysis: catch typing prop inputRange issues the runtime validator misses
            typing_errors = check_typing_props(tsx_content)
            if typing_errors:
                formatted_typing = "\n".join(f"  {e['message']}" for e in typing_errors)
                logger.info(f"[VALIDATE_TSX] Complete: success=False (typing range error) in {(time.time() - func_start)*1000:.2f}ms")
                return {
                    "success": False,
                    "errors": typing_errors,
                    "message": f"[FAILED] Typing prop creates invalid interpolate range:\n{formatted_typing}"
                }

            logger.info(f"[VALIDATE_TSX] TSC passed in {(time.time() - func_start)*1000:.2f}ms, running Remotion runtime validation...")
            remotion_result = await run_remotion_render_validation(temp_file, total_frames)

            if remotion_result.get('success'):
                logger.info(f"[VALIDATE_TSX] Complete: success=True (static + runtime) in {(time.time() - func_start)*1000:.2f}ms")
                return {"success": True, "errors": [], "message": "[PASSED] TSX validation passed (static + runtime)"}
            else:
                error_msg = remotion_result.get('error', 'Unknown runtime error')
                logger.info(f"[VALIDATE_TSX] Complete: success=False (runtime error) in {(time.time() - func_start)*1000:.2f}ms")
                logger.info(f"[VALIDATE_TSX] Remotion error: {error_msg}")
                return {
                    "success": False,
                    "errors": [{"severity": "ERROR", "code": "RUNTIME", "message": error_msg}],
                    "message": f"[FAILED] Remotion runtime error:\n  {error_msg}"
                }

        # Parse errors
        error_output = stderr or stdout
        errors = parse_tsc_errors(error_output)

        if not errors:
            # Static analysis: catch typing prop inputRange issues the runtime validator misses
            typing_errors = check_typing_props(tsx_content)
            if typing_errors:
                formatted_typing = "\n".join(f"  {e['message']}" for e in typing_errors)
                logger.info(f"[VALIDATE_TSX] Complete: success=False (typing range error) in {(time.time() - func_start)*1000:.2f}ms")
                return {
                    "success": False,
                    "errors": typing_errors,
                    "message": f"[FAILED] Typing prop creates invalid interpolate range:\n{formatted_typing}"
                }

            logger.info(f"[VALIDATE_TSX] TSC passed (no actionable errors) in {(time.time() - func_start)*1000:.2f}ms, running Remotion runtime validation...")
            remotion_result = await run_remotion_render_validation(temp_file, total_frames)

            if remotion_result.get('success'):
                logger.info(f"[VALIDATE_TSX] Complete: success=True (static + runtime) in {(time.time() - func_start)*1000:.2f}ms")
                return {"success": True, "errors": [], "message": "[PASSED] TSX validation passed (static + runtime)"}
            else:
                error_msg = remotion_result.get('error', 'Unknown runtime error')
                logger.info(f"[VALIDATE_TSX] Complete: success=False (runtime error) in {(time.time() - func_start)*1000:.2f}ms")
                logger.info(f"[VALIDATE_TSX] Remotion error: {error_msg}")
                return {
                    "success": False,
                    "errors": [{"severity": "ERROR", "code": "RUNTIME", "message": error_msg}],
                    "message": f"[FAILED] Remotion runtime error:\n  {error_msg}"
                }

        # Format and return errors
        formatted = format_errors(errors)
        logger.info(f"[VALIDATE_TSX] Complete: success=False, {len(errors)} errors in {(time.time() - func_start)*1000:.2f}ms")
        logger.debug(f"[VALIDATE_TSX] Errors: {errors}")
        return {
            "success": False,
            "errors": errors,
            "message": f"[FAILED] TSX syntax validation errors:\n{formatted}\n\nSummary: {len(errors)} error(s)"
        }

    except Exception as e:
        logger.error(f"[VALIDATE_TSX] Failed: {type(e).__name__}: {e} in {(time.time() - func_start)*1000:.2f}ms")
        return {"success": False, "errors": [], "message": str(e)}

    finally:
        if temp_file is not None:
            logger.debug(f"[VALIDATE_TSX] Cleanup: removing {temp_file}")
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                logger.debug(f"[VALIDATE_TSX] Temp file removed successfully")
