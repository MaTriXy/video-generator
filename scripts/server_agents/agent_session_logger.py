import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, List

from scripts.path_setup import PROJECT_ROOT as project_root
from scripts.server_agents.transcript_utils import read_jsonl, find_transcript_file
from scripts.controllers.manifest_controller import ManifestController
from scripts.enums import AssetType
from scripts.logging_config import get_agent_logger

logger = get_agent_logger("agent_session_logger")


class AgentSessionLogger:

    def __init__(self, agent_label: str):
        self._agent_label = agent_label
        self._session_log_file: Optional[Path] = None
        self._session_messages_file: Optional[Path] = None
        self._session_video_id: Optional[str] = None

    @property
    def video_id(self) -> Optional[str]:
        return self._session_video_id

    def init_logging(self, video_id: str, asset_type: AssetType) -> None:
        topic_id = f"{video_id}-v2"
        manifest_controller = ManifestController()
        manifest_controller.set_topic(topic_id)
        version = manifest_controller.get_current_gen_version(asset_type)

        log_dir = project_root / "Outputs" / topic_id / asset_type.value / f"v{version}" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._session_log_file = log_dir / f"main_agent_{timestamp}.json"
        self._session_messages_file = log_dir / f"main_agent_{timestamp}_messages.jsonl"
        self._session_video_id = video_id

        self._session_messages_file.touch()

        logger.info(f"Initialized session log: {self._session_log_file}", extra={"video_id": video_id, "step": self._agent_label})

    def append_message(self, message_data: Any) -> None:
        if not self._session_messages_file:
            return

        with open(self._session_messages_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(message_data, ensure_ascii=False, default=str) + "\n")

    def _read_transcript(self, session_id: Optional[str]) -> List[Any]:
        transcript_path = find_transcript_file(session_id) if session_id else None
        vid = self._session_video_id or "--"

        if not transcript_path:
            logger.error(f"Transcript file not found for session: {session_id}", extra={"video_id": vid, "step": self._agent_label})
            return []

        entries = read_jsonl(transcript_path)
        if entries is None:
            return []

        logger.info(f"Read {len(entries)} entries from transcript: {transcript_path}", extra={"video_id": vid, "step": self._agent_label})
        return entries

    def save_transcript(self, session_id: Optional[str]) -> None:
        if not self._session_log_file:
            return

        vid = self._session_video_id or "--"

        try:
            messages = []
            if self._session_messages_file and self._session_messages_file.exists():
                with open(self._session_messages_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            messages.append(json.loads(line))

            transcript = self._read_transcript(session_id)

            log_data = {"messages_logs": messages, "transcript": transcript}
            with open(self._session_log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2, default=str)

            if self._session_messages_file and self._session_messages_file.exists():
                self._session_messages_file.unlink()

            logger.info(f"Saved transcript to: {self._session_log_file}", extra={"video_id": vid, "step": self._agent_label})

        except Exception as e:
            logger.error(f"Failed to save transcript: {e}", exc_info=True, extra={"video_id": vid, "step": self._agent_label})
