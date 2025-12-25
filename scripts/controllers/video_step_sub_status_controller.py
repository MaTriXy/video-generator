import os
from pathlib import Path
from typing import Dict, List
from glob import glob

from scripts.controllers.utils.decorators.try_catch import try_catch
from scripts.enums import AssetType
from scripts.logging_config import get_utility_logger
from scripts.controllers.utils.singleton import SingletonMeta
from scripts.claude_cli.claude_cli_config import ClaudeCliConfig
from scripts.controllers.manifest_controller import ManifestController
from scripts.controllers.video_step_metadata_controller import VideoStepMetadataController

class VideoStepSubStatusController(metaclass=SingletonMeta):

    SINGLE_AGENT_STEPS = {
        AssetType.DIRECTION: [0],
        AssetType.ASSETS: [0]
    }

    SCENE_BASED_STEPS = [AssetType.DESIGN, AssetType.VIDEO]

    def __init__(self):
        self.logger = get_utility_logger('VideoStepSubStatusController')
        self.metadata_controller = VideoStepMetadataController()
        self.manifest_controller = ManifestController()
        self.TOPIC = None

    def set_topic(self, topic: str) -> None:
        self.TOPIC = topic
        ClaudeCliConfig.set_topic(topic)
        self.manifest_controller.set_topic(topic)

    def _is_new_version(self, asset_type: AssetType) -> bool:
        field = self.manifest_controller.get_field(asset_type)
        version = field.get('version', 0)
        current_gen_version = field.get('current_gen_version', 0)
        return version == current_gen_version

    def _get_all_subagents(self, asset_type: AssetType) -> List[int]:
        if asset_type in self.SINGLE_AGENT_STEPS:
            return self.SINGLE_AGENT_STEPS[asset_type]
        elif asset_type in self.SCENE_BASED_STEPS:
            total_scenes = self.metadata_controller.get_total_scenes(asset_type)
            return list(range(total_scenes))
        return []

    def _prompt_files_exist(self, asset_type: AssetType) -> bool:
        prompt_path_template = ClaudeCliConfig.get_prompt_path(asset_type)

        if asset_type in self.SINGLE_AGENT_STEPS:
            prompt_path = prompt_path_template
            return os.path.exists(prompt_path)
        else:
            pattern = prompt_path_template.replace('{scene_index}', '*')
            pattern = str(Path(pattern))
            matching_files = glob(pattern)
            all_subagents = self._get_all_subagents(asset_type)
            expected_files = len(all_subagents)
            return len(matching_files) >= expected_files

    def _get_remaining_subagents(self, asset_type: AssetType) -> List[int]:
        all_subagents = self._get_all_subagents(asset_type)
        completed_subagents = self.manifest_controller.get_subagents_completed(asset_type)
        return [s for s in all_subagents if s not in completed_subagents]

    def _get_available_subagents(self, asset_type: AssetType) -> List[int]:
        all_subagents = self._get_all_subagents(asset_type)
        completed_subagents = self.manifest_controller.get_subagents_completed(asset_type)
        claimed_subagents = self.manifest_controller.get_subagents_claimed(asset_type)
        return [s for s in all_subagents if s not in completed_subagents and s not in claimed_subagents]

    @try_catch
    def claim_next_subagent(self, asset_type: AssetType) -> Dict[str, any]:
        available = self._get_available_subagents(asset_type)

        if not available:
            return {'success': False, 'scene_index': -1, 'message': 'No available scenes to claim'}

        for subagent_id in available:
            if self.manifest_controller.claim_subagent(asset_type, subagent_id):
                return {'success': True, 'scene_index': subagent_id, 'message': f'Claimed scene {subagent_id}'}

        return {'success': False, 'scene_index': -1, 'message': 'All scenes claimed by other agents'}

    @try_catch
    def get_next_step(self, asset_type: AssetType) -> Dict[str, any]:
        if self._is_new_version(asset_type):
            return {
                'action': 'run_preprocessing',
                'subagents': []
            }

        if not self._prompt_files_exist(asset_type):
            return {
                'action': 'run_preprocessing',
                'subagents': []
            }

        remaining_subagents = self._get_remaining_subagents(asset_type)

        if len(remaining_subagents) == 0:
            return {
                'action': 'run_post_processing',
                'subagents': []
            }

        self.manifest_controller.clear_claimed_agents(asset_type)

        return {
            'action': 'run_subagents',
            'subagents': remaining_subagents
        }

    @try_catch
    def mark_subagent_completed(self, asset_type: AssetType, subagent_id: int) -> bool:
        return self.manifest_controller.mark_subagent_completed(asset_type, subagent_id)
