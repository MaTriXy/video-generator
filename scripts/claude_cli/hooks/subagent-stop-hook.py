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


class SubagentStopHook(BaseHook):
    """Hook that executes when a subagent stops."""

    def __init__(self, input_data: Dict[str, Any]):
        super().__init__(
            hook_name="subagent-stop-hook",
            input_data=input_data,
            agents=["hook_test"],
        )

    def should_run_hook(self) -> bool:
        try:
            date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            is_file_read, file_path = self.was_file_read()
            if is_file_read:
                path_name = f"scene_hook_started_{date_string}.log"
                # info_log(f"file_read: {is_file_read}", path_name)
            return is_file_read
        except Exception as e:
            error_message = f"Error in should_run_hook: {str(e)}"
            error_log(error_message, str(e), "","subagent-stop-hook_error.log")
            sys.exit(0)

    def was_prompt_file_read(self) -> tuple:
        try:
            query = {
                "and": [
                    {"eq": {"field": "message.content[*].type", "value": "tool_use"}},
                    {"eq": {"field": "message.content[*].name", "value": "Read"}},
                    {"contains": {"field": "message.content[*].input.file_path", "value": "prompt"}}
                ]
            }
            matched, entry = self.match_transcript(query)
            # date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # path_name = f"was_prompt_file_read_{date_string}.log"
            # info_log(f"{json.dumps(entry)}", path_name)

            if matched and entry:
                file_path = self.extract_value(entry, "message.content[*].input.file_path")
                if file_path:
                    # Extract prompt index from filename (e.g., prompt_0.md -> 0)
                    filename = os.path.basename(file_path)
                    match = re.search(r'prompt_(\d+)\.md', filename)
                    prompt_index = match.group(1) if match else "root"

                    # Get parent folder names (not full paths)
                    # file_path: C:\...\Outputs\Video\Prompts\prompt_0.md
                    prompts_folder_path = os.path.dirname(file_path)  # .../Outputs/Video/Prompts
                    asset_folder_path = os.path.dirname(prompts_folder_path)  # .../Outputs/Video
                    topic_folder_path = os.path.dirname(asset_folder_path)  # .../Outputs

                    # Extract just the folder names
                    asset_folder_name = os.path.basename(asset_folder_path)  # "Video"
                    topic_folder_name = os.path.basename(topic_folder_path)  # "Outputs" or topic name

                    self.log_file_path = f"{date_string}_{topic_folder_name}_{asset_folder_name}_{prompt_index}.log"
                    return True, 
            return False
        except Exception as e:
            error_message = f"Error in was_prompt_file_read: {str(e)}"
            error_log(error_message, str(e), "subagent-stop-hook_error.log")
            return False, None, None, None


    def was_file_read(self) -> bool:
        """Check if a prompt file was read using the Query DSL."""
        try:

            query = {
                "and": [
                    {"eq": {"field": "message.content[*].type", "value": "tool_use"}},
                    {"eq": {"field": "message.content[*].name", "value": "Read"}},
                    {"contains": {"field": "message.content[*].input.file_path", "value": "Outputs\\Video\\Prompts\\prompt_"}}
                ]
            }

            matched, entry = self.match_transcript(query)
            # date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # path_name = f"was_file_read_{date_string}.log"
            # info_log(f"{json.dumps(entry)}", path_name)
            if matched and entry:
                return True, self.extract_value(entry, "message.content[*].input.file_path")

            return False, None
        except Exception as e:
            error_message = f"Error in was_file_read: {str(e)}"
            error_log(error_message, str(e), "subagent-stop-hook_error.log")
            return False, None

    def check_tsx_file_creation(self) -> str:
        try:
            # Query: Find user entries with toolUseResult.type in ["create", "update"]
            # AND toolUseResult.filePath ends with "video_output.tsx"
            query = {
                "and": [
                    {"or": [
                        {"eq": {"field": "toolUseResult.type", "value": "create"}},
                        {"eq": {"field": "toolUseResult.type", "value": "update"}}
                    ]},
                    {"contains": {"field": "toolUseResult.filePath", "value": "Outputs\\Video\\Latest\\scene_"}},
                    {"endswith": {"field": "toolUseResult.filePath", "value": ".tsx"}}
                ]
            }

            matched, file_path = self.match_transcript(query, return_field="toolUseResult.filePath")
            return matched, file_path
        except Exception as e:
            error_message = f"Error in check_tsx_file_creation: {str(e)}"
            error_log(error_message, str(e), "subagent-stop-hook_error.log")
            return False, None

    def validate_input(self) -> bool:
        try:
            date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            is_file_created, file_path = self.check_tsx_file_creation()
            if not is_file_created:
                path_name = f"file_not_created_subagent-stop-hook_{date_string}.log"
                info_log(f"file_created: {is_file_created}, file_path: {file_path}", path_name)
                print("The scene file was not created at Outputs/Video/Latest/scene_{scene_index}.tsx.", file=sys.stderr)
                sys.exit(2)
            sys.exit(0)
        except Exception as e:
            error_message = f"Error in validate_input: {str(e)}"
            error_log(error_message, str(e), "subagent-stop-hook_error.log")
            return False


if __name__ == "__main__":
    try:
        date_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path_name = f"all_hooks_started_{date_string}.log"
        info_log(f"all_hooks_started: {path_name}", path_name)

        input_data = read_stdin()
        hook = SubagentStopHook(input_data)
        if hook.run():
            hook.validate_input()
    except Exception as e:
        error_message = f"Error in subagent-stop-hook: {str(e)}"
        error_log(error_message, str(e), "subagent-stop-hook_error.log")
