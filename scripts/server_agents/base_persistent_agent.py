import dataclasses
import os
from pathlib import Path
from typing import Optional, Tuple, Any, List, Union

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, SystemMessage
from claude_agent_sdk.types import ResultMessage

from scripts.path_setup import PROJECT_ROOT as project_root, PROMPTS_DIR

from scripts.server_agents.claude_sdk_config import (
    get_step_name,
    get_preprocessing_class,
    get_tools,
    get_disallowed_tools,
    get_model,
    get_effort,
    get_config,
)
from scripts.server_agents.transcript_utils import find_transcript_file
from scripts.server_agents.agent_session_logger import AgentSessionLogger
from scripts.server_agents.agent_completion_handler import send_step_completion
from scripts.server_agents.video_update_backend_notifier import send_failure_to_backend
from scripts.server_agents.prompt_utils import cleanup_prompts
from scripts.enums import AssetType
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.manifest_controller import ManifestController
from scripts.logging_config import get_agent_logger, set_console_logging
from scripts.utility.config import ADD_EMOTIONS

logger = get_agent_logger("base_persistent_agent")



class BasePersistentAgent:

    def __init__(self, asset_type: AssetType):
        config = get_config(asset_type)

        self.asset_type = asset_type
        self.subagent_name = config["subagent_name"]
        self.step_name = config["step_name"]
        self.settings_folder = config["settings_folder"]
        self.output_folder = config["output_folder"]
        self.agent_label = config["agent_label"]
        self.multi_prompt = config["multi_prompt"]
        self._oauth_token = config["oauth_token"]

        self._system_prompt = self._get_system_prompt()
        self._client = ClaudeSDKClient(self._build_options())
        self._connected = False

        self._session_id: Optional[str] = None
        self._last_subagent_agent_id: Optional[str] = None
        self._last_cost_usd: Optional[float] = None
        self._last_duration_ms: Optional[float] = None
        self._last_usage: Optional[dict] = None

        self._session_logger = AgentSessionLogger(self.agent_label)

    # ── Template methods (override in subclasses) ──────────────────────

    def _get_system_prompt(self) -> str:
        return ""

    def _get_tools(self) -> list:
        """Return the tools list for this agent. Base: step tools only (no Task)."""
        return get_tools(self.asset_type)

    def _get_hooks(self) -> dict:
        """Return hooks dict for ClaudeAgentOptions. Base: no hooks."""
        return {}

    def _get_extra_args(self) -> dict:
        """Return extra_args for ClaudeAgentOptions."""
        return {"disable-slash-commands": None}

    def _build_query_prompt(self, video_id: str, prompt_result: Union[str, List[str]]) -> str:
        return ""

    def _build_resume_prompt(self, agent_id: str, resume_prompt: Optional[str] = None) -> str:
        return ""

    # ── Options building ───────────────────────────────────────────────

    def _build_options(self, resume_session_id: Optional[str] = None) -> ClaudeAgentOptions:
        extra_args = self._get_extra_args()

        kwargs = dict(
            tools=self._get_tools(),
            disallowed_tools=get_disallowed_tools(self.asset_type),
            permission_mode="bypassPermissions",
            model=get_model(self.asset_type),
            setting_sources=["project"],
            env={"CLAUDE_CODE_OAUTH_TOKEN": self._oauth_token, "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "64000", "CLAUDE_CODE_SUBAGENT_MODEL": "claude-opus-4-6"},
            extra_args=extra_args,
            hooks=self._get_hooks(),
            stderr=lambda line: logger.warning(f"[CLI stderr] {line}", extra={"video_id": "--", "step": self.agent_label}),
            thinking={"type": "adaptive"},
            effort=get_effort(self.asset_type)
        )

        if self.settings_folder:
            kwargs["cwd"] = self.settings_folder if Path(self.settings_folder).is_absolute() else str(project_root / "claude_settings" / self.settings_folder)

        if "system-prompt-file" in extra_args:
            kwargs["system_prompt"] = ""
        else:
            kwargs["system_prompt"] = self._system_prompt

        if resume_session_id:
            kwargs["resume"] = resume_session_id
        return ClaudeAgentOptions(**kwargs)

    # ── Connection lifecycle ───────────────────────────────────────────

    async def _connect(self, session_id: Optional[str] = None) -> None:
        if not self._connected:
            logger.info(f"Connecting...", extra={"video_id": "--", "step": self.agent_label})

            if session_id:
                logger.info(f"Creating client with resume={session_id}", extra={"video_id": "--", "step": self.agent_label})
                self._client = ClaudeSDKClient(self._build_options(resume_session_id=session_id))

            await self._client.connect()
            self._connected = True
            logger.info("Connected", extra={"video_id": "--", "step": self.agent_label})

    async def _disconnect(self) -> None:
        if self._connected:
            vid = self._session_logger.video_id or "--"
            logger.info("Disconnecting agent", extra={"video_id": vid, "step": self.agent_label})
            self._session_logger.save_transcript(self._session_id)
            await self._client.disconnect()
            self._connected = False
            logger.info("Agent disconnected", extra={"video_id": vid, "step": self.agent_label})

    # ── Response handling ──────────────────────────────────────────────

    async def _receive_and_log_responses(self, video_id: str) -> Tuple[Any, int, str]:
        message_count = 0
        last_text = ""
        result = None
        self._last_cost_usd = None
        self._last_duration_ms = None
        self._last_usage = None

        async for message in self._client.receive_response():
            message_count += 1

            if isinstance(message, SystemMessage):
                if hasattr(message, 'data') and isinstance(message.data, dict):
                    session_id = message.data.get('session_id')
                    if session_id:
                        self._session_id = session_id
                        logger.info(f"Session ID: {self._session_id}", extra={"video_id": video_id, "step": self.agent_label})

            if isinstance(message, ResultMessage):
                self._last_cost_usd = getattr(message, 'total_cost_usd', None)
                self._last_duration_ms = getattr(message, 'duration_ms', None)
                self._last_usage = getattr(message, 'usage', None)

            try:
                message_data = dataclasses.asdict(message)
            except TypeError:
                message_data = {"type": type(message).__name__, "data": str(message)}
            message_data["_type"] = type(message).__name__

            self._session_logger.append_message(message_data)

        return (result, message_count, last_text)

    def _save_user_prompt(self, video_id: str, resume_prompt: str) -> None:
        topic_id = f"{video_id}-v2"
        cli_config = ClaudeCliConfig(topic_id)
        prompt_path = cli_config.get_prompt_path(self.asset_type)
        prompts_dir = Path(prompt_path).parent
        user_prompt_file = project_root / prompts_dir / "user-prompt.md"

        user_prompt_file.parent.mkdir(parents=True, exist_ok=True)

        with open(user_prompt_file, "a", encoding="utf-8") as f:
            f.write(f"\n-------------\n{resume_prompt}")

        logger.info(f"Appended user prompt to: {user_prompt_file}", extra={"video_id": video_id, "step": self.agent_label})

    async def _send_completion_callback(self, video_id: str, step_type: str) -> None:
        transcript_path = find_transcript_file(self._session_id) if self._session_id else None
        await send_step_completion(
            video_id=video_id,
            step_type=step_type,
            asset_type=self.asset_type,
            agent_label=self.agent_label,
            session_id=self._session_id,
            agent_id=self._last_subagent_agent_id,
            transcript_path=transcript_path,
            cost_usd=self._last_cost_usd,
            duration_ms=self._last_duration_ms,
            usage=self._last_usage,
        )

    # ── Main entry points ──────────────────────────────────────────────

    async def resume_agent(self, video_id: str, agent_id: str, resume_prompt: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[Any, int, str]:
        step_type = get_step_name(self.asset_type)

        logger.info(f"Starting resume_agent: agent={agent_id}, session={session_id}", extra={"video_id": video_id, "step": self.agent_label})

        try:
            await self._connect(session_id=session_id)
        except Exception as e:
            logger.error(f"Connection failed during resume: {e}", exc_info=True, extra={"video_id": video_id, "step": self.agent_label})
            await send_failure_to_backend(video_id, step_type, f"Agent connection failed: {e}", session_id)
            raise

        try:
            topic_id = f"{video_id}-v2"
            manifest_controller = ManifestController()
            manifest_controller.set_topic(topic_id)
            manifest_controller.increment_gen_version(self.asset_type)

            self._session_logger.init_logging(video_id, self.asset_type)

            query_prompt = self._build_resume_prompt(agent_id, resume_prompt)

            if resume_prompt:
                self._save_user_prompt(video_id, resume_prompt)

            if session_id:
                await self._client.query(prompt=query_prompt, session_id=session_id)
            else:
                await self._client.query(prompt=query_prompt)

            result = await self._receive_and_log_responses(video_id)
            logger.info(f"resume_agent completed successfully (messages={result[1]})", extra={"video_id": video_id, "step": self.agent_label})
            await self._send_completion_callback(video_id, step_type)
            return result
        except Exception as e:
            logger.error(f"Resume execution failed: {e}", exc_info=True, extra={"video_id": video_id, "step": self.agent_label})
            await send_failure_to_backend(video_id, step_type, f"Resume execution failed: {e}", session_id)
            raise
        finally:
            await self._disconnect()

    async def query_agent(self, video_id: str) -> Tuple[Any, int, str]:
        step_type = get_step_name(self.asset_type)
        topic_id = f"{video_id}-v2"

        logger.info(f"Starting query_agent for topic: {topic_id}", extra={"video_id": video_id, "step": self.agent_label})

        # Skip agent entirely for audio when skipAudioApiCall is set (batch mode — audio reused from primary)
        if self.asset_type == AssetType.AUDIO:
            manifest_controller = ManifestController()
            manifest_controller.set_topic(topic_id)
            metadata = manifest_controller.get_metadata() or {}
            if metadata.get("skipAudioApiCall"):
                logger.info("skipAudioApiCall=True, skipping audio agent — running post-processing directly", extra={"video_id": video_id, "step": self.agent_label})
                manifest_controller.increment_gen_version(self.asset_type)
                await self._send_completion_callback(video_id, step_type)
                return (None, 0, "")

        # Skip emotion agent for audio when ADD_EMOTIONS is disabled
        if self.asset_type == AssetType.AUDIO and not ADD_EMOTIONS:
            logger.info("ADD_EMOTIONS=false, skipping emotion agent — running post-processing directly", extra={"video_id": video_id, "step": self.agent_label})
            manifest_controller = ManifestController()
            manifest_controller.set_topic(topic_id)
            manifest_controller.increment_gen_version(self.asset_type)
            await self._send_completion_callback(video_id, step_type)
            return (None, 0, "")

        # Clean up stale prompts from previous runs
        cleanup_prompts(topic_id, self.step_name)

        try:
            logger.info(f"Running preprocessing for: {topic_id}", extra={"video_id": video_id, "step": self.agent_label})
            preprocess_class = get_preprocessing_class(self.asset_type)
            preprocessor = preprocess_class(topic=topic_id)
            prompt_result: Union[str, List[str]] = preprocessor.run()
            set_console_logging(True)

            if prompt_result is None:
                logger.info("Preprocessor signalled skip — running post-processing directly", extra={"video_id": video_id, "step": self.agent_label})
                await self._send_completion_callback(video_id, step_type)
                return (None, 0, "")

            prompt_count = len(prompt_result) if isinstance(prompt_result, list) else 1
            logger.info(f"Preprocessing produced {prompt_count} prompt(s)", extra={"video_id": video_id, "step": self.agent_label})
        except Exception as e:
            set_console_logging(True)
            logger.error(f"Preprocessing failed: {e}", exc_info=True, extra={"video_id": video_id, "step": self.agent_label})
            await send_failure_to_backend(video_id, step_type, f"Preprocessing failed: {e}")
            raise

        # Prepare query via template method (handles active prompts + query building)
        try:
            query_prompt = self._build_query_prompt(video_id, prompt_result)
        except Exception as e:
            logger.error(f"Failed to prepare query: {e}", exc_info=True, extra={"video_id": video_id, "step": self.agent_label})
            await send_failure_to_backend(video_id, step_type, f"Failed to prepare query: {e}")
            raise

        try:
            self._session_logger.init_logging(video_id, self.asset_type)
        except Exception as e:
            logger.error(f"Session logging init failed: {e}", exc_info=True, extra={"video_id": video_id, "step": self.agent_label})
            cleanup_prompts(topic_id, self.step_name)
            await send_failure_to_backend(video_id, step_type, f"Session logging init failed: {e}")
            raise

        try:
            await self._connect()
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True, extra={"video_id": video_id, "step": self.agent_label})
            cleanup_prompts(topic_id, self.step_name)
            await send_failure_to_backend(video_id, step_type, f"Agent connection failed: {e}")
            raise

        try:
            logger.debug(f"System prompt: {self._system_prompt}", extra={"video_id": video_id, "step": self.agent_label})
            logger.debug(f"Query prompt: {query_prompt}", extra={"video_id": video_id, "step": self.agent_label})
            await self._client.query(prompt=query_prompt)
            logger.info("Query sent, receiving responses...", extra={"video_id": video_id, "step": self.agent_label})
            result = await self._receive_and_log_responses(video_id)
            logger.info(f"query_agent completed successfully (messages={result[1]})", extra={"video_id": video_id, "step": self.agent_label})
            await self._send_completion_callback(video_id, step_type)
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}", exc_info=True, extra={"video_id": video_id, "step": self.agent_label})
            cleanup_prompts(topic_id, self.step_name)
            await send_failure_to_backend(video_id, step_type, f"Query execution failed: {e}")
            raise
        finally:
            await self._disconnect()
