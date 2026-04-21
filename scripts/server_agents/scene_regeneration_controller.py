"""
Scene Regeneration Controller — Regenerates specific video scenes without affecting others.

Extends SubagentExecution with a custom query_agent() flow that:
  - Deletes only the targeted scene files from Latest/
  - Deletes all old prompts and builds new ones for requested scenes only
  - Dispatches the orchestrator agent, then triggers full post-processing (rebuild + deploy)
"""

import json
from pathlib import Path
from typing import List, Tuple

from scripts.path_setup import PROJECT_ROOT as project_root
from scripts.enums import AssetType
from scripts.server_agents.step_execution_controllers.subagent_execution import SubagentExecution
from scripts.server_agents.base_persistent_agent import logger
from scripts.server_agents.claude_sdk_config import get_step_name
from scripts.server_agents.prompt_utils import cleanup_prompts
from scripts.server_agents.video_update_backend_notifier import send_failure_to_backend
from scripts.claude_cli.content_video.pre_process import VideoPreProcess
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.utils.system_io_controller import SystemIOController
from scripts.logging_config import set_console_logging


class SceneRegenerationAgent(SubagentExecution):
    """Regenerates specific video scenes without affecting other scene files."""

    def __init__(self, scene_indices: List[int]):
        super().__init__(AssetType.VIDEO)
        self.scene_indices = sorted(set(scene_indices))

    # ── Overridden entry point ────────────────────────────────────────

    async def query_agent(self, video_id: str):
        """Custom flow: selective deletion, scene-specific prompts, full rebuild."""
        step_type = get_step_name(self.asset_type)
        topic_id = f"{video_id}-v2"

        logger.info(
            f"Scene regeneration starting: scenes={self.scene_indices}",
            extra={"video_id": video_id, "step": self.agent_label},
        )

        # Clean up stale active/claimed prompts from previous runs
        cleanup_prompts(topic_id, self.step_name)

        # Increment gen version so post-processing writes to a new v{n}/ directory
        manifest_controller = ManifestController()
        manifest_controller.set_topic(topic_id)
        manifest_controller.increment_gen_version(self.asset_type)

        # ── Preprocessing ─────────────────────────────────────────────
        try:
            self._delete_target_scene_files(topic_id)
            self._delete_prompt_files(topic_id)
            prompt_paths = self._build_scene_prompts(topic_id)
            set_console_logging(True)

            logger.info(
                f"Built {len(prompt_paths)} prompt(s) for scenes {self.scene_indices}",
                extra={"video_id": video_id, "step": self.agent_label},
            )
        except Exception as e:
            set_console_logging(True)
            logger.error(
                f"Preprocessing failed: {e}", exc_info=True,
                extra={"video_id": video_id, "step": self.agent_label},
            )
            await send_failure_to_backend(video_id, step_type, f"Scene regen preprocessing failed: {e}")
            raise

        # ── Build query ───────────────────────────────────────────────
        try:
            query_prompt = self._build_query_prompt(video_id, prompt_paths)
        except Exception as e:
            logger.error(
                f"Query build failed: {e}", exc_info=True,
                extra={"video_id": video_id, "step": self.agent_label},
            )
            await send_failure_to_backend(video_id, step_type, f"Query build failed: {e}")
            raise

        # ── Logging init ──────────────────────────────────────────────
        try:
            self._session_logger.init_logging(video_id, self.asset_type)
        except Exception as e:
            logger.error(
                f"Logging init failed: {e}", exc_info=True,
                extra={"video_id": video_id, "step": self.agent_label},
            )
            cleanup_prompts(topic_id, self.step_name)
            await send_failure_to_backend(video_id, step_type, f"Logging init failed: {e}")
            raise

        # ── Connect ───────────────────────────────────────────────────
        try:
            await self._connect()
        except Exception as e:
            logger.error(
                f"Connection failed: {e}", exc_info=True,
                extra={"video_id": video_id, "step": self.agent_label},
            )
            cleanup_prompts(topic_id, self.step_name)
            await send_failure_to_backend(video_id, step_type, f"Connection failed: {e}")
            raise

        # ── Dispatch & await ──────────────────────────────────────────
        try:
            await self._client.query(prompt=query_prompt)
            logger.info(
                "Query sent, receiving responses...",
                extra={"video_id": video_id, "step": self.agent_label},
            )
            result = await self._receive_and_log_responses(video_id)
            logger.info(
                f"Scene regeneration completed (messages={result[1]})",
                extra={"video_id": video_id, "step": self.agent_label},
            )
            await self._send_completion_callback(video_id, step_type)
            return result
        except Exception as e:
            logger.error(
                f"Execution failed: {e}", exc_info=True,
                extra={"video_id": video_id, "step": self.agent_label},
            )
            cleanup_prompts(topic_id, self.step_name)
            await send_failure_to_backend(video_id, step_type, f"Scene regen failed: {e}")
            raise
        finally:
            await self._disconnect()

    # ── Scene-specific file operations ────────────────────────────────

    def _delete_target_scene_files(self, topic_id: str) -> None:
        """Delete only the scene .tsx files for the requested scene indices."""
        cli_config = ClaudeCliConfig(topic_id)
        latest_path = cli_config.get_latest_path(AssetType.VIDEO)
        latest_dir = Path(latest_path).parent

        for idx in self.scene_indices:
            scene_file = latest_dir / f"scene_{idx}.tsx"
            if scene_file.exists():
                scene_file.unlink()
                logger.info(
                    f"Deleted scene_{idx}.tsx from Latest/",
                    extra={"video_id": topic_id, "step": self.agent_label},
                )

    def _delete_prompt_files(self, topic_id: str) -> None:
        """Delete all prompt files from the Video/Prompts directory."""
        prompts_dir = Path(project_root) / "Outputs" / topic_id / "Video" / "Prompts"
        if not prompts_dir.exists():
            return
        for f in prompts_dir.iterdir():
            if f.is_file():
                f.unlink()

    # ── Prompt building ───────────────────────────────────────────────

    def _build_scene_prompts(self, topic_id: str) -> List[str]:
        """Build prompts for only the requested scenes, reusing VideoPreProcess helpers."""
        preprocessor = VideoPreProcess(topic=topic_id, gen_prompt=False)

        # Load data without calling run()
        preprocessor.video_direction = preprocessor.output_controller.read_output(AssetType.DIRECTION)
        if not preprocessor.video_direction:
            raise ValueError("No video direction found. Direction step may not have completed.")

        preprocessor.asset_manifest = preprocessor.output_controller.read_output(AssetType.ASSETS)
        if not preprocessor.asset_manifest:
            raise ValueError("No asset manifest found. Assets step may not have completed.")

        preprocessor.transcript = preprocessor.get_audio_transcript()

        # Validate scene indices
        total_scenes = len(preprocessor.video_direction.get("scenes", []))
        for idx in self.scene_indices:
            if idx >= total_scenes:
                raise ValueError(f"Scene index {idx} out of range (total scenes: {total_scenes})")

        # Shared header (aspect ratio, viewport, artstyle)
        course_metadata = preprocessor.get_metadata()
        artstyle_json = preprocessor.load_artstyle("code")
        shared_header = (
            f"<video_aspect_ratio>{course_metadata.get('video_ratio', '')}</video_aspect_ratio>\n"
            f"<viewport_width>{course_metadata.get('viewport_width', '')}</viewport_width>\n"
            f"<viewport_height>{course_metadata.get('viewport_height', '')}</viewport_height>"
            f"<artstyle>{artstyle_json}</artstyle>\n"
        )

        # Build per-scene prompt content and collect assets
        video_id = topic_id.removesuffix("-v2")
        scene_prompts = {}
        scene_assets_map = {}

        for scene_index in self.scene_indices:
            variables = preprocessor.build_prompt_variables(scene_index=scene_index)
            prompt = preprocessor.build_prompt(variables=variables, append_date=False)
            scene_prompts[scene_index] = (
                f"<video_id>{video_id}</video_id>\n"
                f"<scene_index>{scene_index}</scene_index>\n\n{prompt}"
            )

            scene_direction = preprocessor.get_scene_direction(scene_index)
            asset_names = preprocessor.get_scene_asset_names(scene_direction)
            scene_assets_map[scene_index] = preprocessor.get_filtered_asset_manifest(asset_names)

        # Token-aware splitting
        batches = self._split_by_tokens(
            self.scene_indices, scene_prompts, scene_assets_map, shared_header, preprocessor
        )

        # Save prompt files
        prompts_dir = Path(project_root) / "Outputs" / topic_id / "Video" / "Prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        file_io = SystemIOController()
        prompt_paths = []

        for batch_indices, combined_prompt in batches:
            prompt_filename = f"prompt_{batch_indices[0]}_{batch_indices[-1]}.md"
            prompt_path = prompts_dir / prompt_filename
            original_path = prompt_path.with_stem(prompt_path.stem + "_original")

            file_io.write_text(str(original_path), combined_prompt)
            file_io.write_text(str(prompt_path), " ".join(combined_prompt.split()))
            prompt_paths.append(str(prompt_path.resolve()))

            logger.info(
                f"Saved prompt: {prompt_filename} (scenes {batch_indices})",
                extra={"video_id": topic_id, "step": self.agent_label},
            )

        return prompt_paths

    # ── Prompt assembly & token splitting ─────────────────────────────

    def _assemble_prompt(
        self,
        indices: List[int],
        scene_prompts: dict,
        scene_assets_map: dict,
        shared_header: str,
    ) -> str:
        """Combine scene prompts into a single batched prompt string."""
        parts = [f"# Scene {i}\n\n{scene_prompts[i]}" for i in indices]
        scenes_section = "\n\n---\n\n".join(parts)

        seen = set()
        batch_assets = []
        for i in indices:
            for asset in scene_assets_map[i]:
                name = asset.get("name")
                if name and name not in seen:
                    seen.add(name)
                    batch_assets.append(asset)

        asset_json = json.dumps(batch_assets, indent=2) if batch_assets else "[]"
        return f"{shared_header}\n\n---\n\n{scenes_section}\n\n---\n\n<asset_manifest>{asset_json}</asset_manifest>"

    def _split_by_tokens(
        self,
        indices: List[int],
        scene_prompts: dict,
        scene_assets_map: dict,
        shared_header: str,
        preprocessor: VideoPreProcess,
    ) -> List[Tuple[List[int], str]]:
        """Recursively split scene batches until each is under the token limit."""
        combined = self._assemble_prompt(indices, scene_prompts, scene_assets_map, shared_header)
        token_count = preprocessor._count_tokens(combined)

        if token_count <= preprocessor.TOKEN_LIMIT or len(indices) <= 1:
            return [(indices, combined)]

        mid = len(indices) // 2
        left = self._split_by_tokens(indices[:mid], scene_prompts, scene_assets_map, shared_header, preprocessor)
        right = self._split_by_tokens(indices[mid:], scene_prompts, scene_assets_map, shared_header, preprocessor)
        return left + right
