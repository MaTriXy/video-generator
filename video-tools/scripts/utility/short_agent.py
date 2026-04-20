"""
ShortAgent - Lightweight wrapper for single-turn LLM calls via Claude Agent SDK.
"""

import os
import time
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
from scripts.logging_config import get_utility_logger

logger = get_utility_logger('utility.short_agent')

AGENT_LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "agentlogs"


class ShortAgent:
    """Single-turn LLM agent for quick tasks like keyword suggestion and ranking."""

    def __init__(self, system_prompt: str, name: str = "", model: str = "sonnet"):
        self.model = model
        self.system_prompt = system_prompt
        self.name = name

    def _save_log(self, prompt: str, result: str, suffix: str = ""):
        """Save system prompt, prompt, and result to agentlogs/<name>/ folder."""
        log_dir = AGENT_LOGS_DIR / self.name if self.name else AGENT_LOGS_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        parts = [self.name, timestamp] if self.name else [timestamp]
        if suffix:
            parts.append(suffix)
        log_file = log_dir / f"{'_'.join(parts)}.md"
        log_file.write_text(
            f"## System Prompt\n{self.system_prompt}\n\n"
            f"## Prompt\n{prompt}\n\n"
            f"## Result\n{result}\n",
            encoding="utf-8",
        )

    def _build_options(self) -> ClaudeAgentOptions:
        env = {}
        oauth_token = os.environ.get("BASIC_CLAUDE_CODE_TOKEN")
        if oauth_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
        self._stderr_lines = []
        return ClaudeAgentOptions(
            model=self.model,
            max_turns=1,
            system_prompt=self.system_prompt,
            env=env,
            stderr=lambda line: self._stderr_lines.append(line),
        )

    @staticmethod
    def _extract_text(message) -> str:
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    return block.text.strip()
        return ""

    def _log_failure(self, method: str, messages_received: list, error: Exception):
        stderr_output = "\n".join(self._stderr_lines) if self._stderr_lines else "no stderr captured"
        logger.error(f"[ShortAgent:{self.name}] claude_agent_sdk failed ({method}): {error}")
        logger.error(f"[ShortAgent:{self.name}] stderr: {stderr_output}")
        logger.error(f"[ShortAgent:{self.name}] messages received before crash: {messages_received}")

    async def ask(self, prompt: str, suffix: str = "") -> str:
        """Send a single-turn prompt and return the text response."""
        options = self._build_options()
        result = ""
        received = []
        try:
            async for message in query(prompt=prompt, options=options):
                received.append(repr(message))
                text = self._extract_text(message)
                if text:
                    result = text
        except Exception as e:
            self._log_failure("ask", received, e)
            raise
        return result

    async def ask_with_images(self, text: str, images: list[dict], suffix: str = "") -> str:
        """
        Send a multimodal prompt (text + base64 images) and return the text response.
        images: list of {"data": base64_str, "media_type": "image/png"}
        """
        content = []
        for img in images:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": img["media_type"], "data": img["data"]},
            })
        content.append({"type": "text", "text": text})

        async def _stream():
            yield {"type": "user", "message": {"role": "user", "content": content}}

        options = self._build_options()
        result = ""
        received = []
        try:
            async for message in query(prompt=_stream(), options=options):
                received.append(repr(message))
                text_val = self._extract_text(message)
                if text_val:
                    result = text_val
        except Exception as e:
            self._log_failure("ask_with_images", received, e)
            raise
        return result
