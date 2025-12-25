from datetime import datetime
import json
import sys
import os
import re
from typing import Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.claude_cli.content_video.validation_process import SceneValidateProcess
from scripts.claude_cli.hooks.base_hook import BaseHook, error_log, info_log, read_stdin
from scripts.controllers.manifest_controller import ManifestController
from scripts.enums import AssetType


class SubagentStopHook(BaseHook):
    """Hook that executes when a subagent stops."""

    def __init__(self, input_data: Dict[str, Any]):
        super().__init__(
            hook_name="subagent-stop-hook",
            input_data=input_data,
            agents=["hook_test"],
        )

    def should_run_hook(self) -> bool:
        return True

    def set_log_path(self) -> None:
        """Set the log file path based on file read from transcript in Outputs folder."""
        try:
            query = {
                "and": [
                    {"eq": {"field": "message.content[*].type", "value": "tool_use"}},
                    {"eq": {"field": "message.content[*].name", "value": "Read"}},
                    {"contains": {"field": "message.content[*].input.file_path", "value": "Outputs"}}
                ]
            }
            matched, entry = self.match_transcript(query)
            date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            if matched and entry:
                file_path = self.extract_value(entry, "message.content[*].input.file_path")
                if file_path:
                    filename = os.path.basename(file_path)
                    match = re.search(r'(?:prompt_|scene_)(\d+)', filename)
                    prompt_index = match.group(1) if match else None

                    topic_folder_name = None
                    asset_folder_name = None
                    normalized_path = file_path.replace("\\", "/")
                    if "Outputs/" in normalized_path:
                        after_outputs = normalized_path.split("Outputs/")[1]
                        parts = after_outputs.split("/")
                        topic_folder_name = parts[0] if len(parts) > 0 else None
                        asset_folder_name = parts[1] if len(parts) > 1 else None

                    if topic_folder_name and asset_folder_name:
                        try:
                            manifest_controller = ManifestController()
                            manifest_controller.set_topic(topic_folder_name)
                            asset_type = AssetType(asset_folder_name)
                            version = manifest_controller.get_current_gen_version(asset_type)
                        except Exception:
                            version = 0

                        log_dir = os.path.join("Outputs", topic_folder_name, asset_folder_name, f"v{version}")
                        if prompt_index:
                            log_filename = f"{date_string}_{topic_folder_name}_{asset_folder_name}_{prompt_index}.log"
                        else:
                            log_filename = f"{date_string}_{topic_folder_name}_{asset_folder_name}.log"
                        self.log_file_path = os.path.join(log_dir, log_filename)
                        return

            # Fallback - save in Outputs/hooks_logs
            log_dir = os.path.join("Outputs", "hooks_logs")
            log_filename = f"{date_string}_unknown.log"
            self.log_file_path = os.path.join(log_dir, log_filename)

        except Exception as e:
            error_log(f"Error in set_log_path: {str(e)}", str(e), "", "subagent-stop-hook_error.log")
            # Fallback path on error
            date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.log_file_path = os.path.join("Outputs", "hooks_logs", f"{date_string}_error.log")

if __name__ == "__main__":
    try:
        date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path_name = f"all_hooks_started_{date_string}.log"
        info_log(f"all_hooks_started: {path_name}", path_name)

        input_data = read_stdin()
        hook = SubagentStopHook(input_data)
        hook.run()
    except Exception as e:
        error_message = f"Error in subagent-stop-hook: {str(e)}"
        error_log(error_message, str(e), "subagent-stop-hook_error.log")
