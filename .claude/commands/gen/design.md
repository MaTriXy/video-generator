---
description: generate video design specifications by following the instructions given below.
allowed-tools: Task, SlashCommand
model: sonnet
argument-hint: --topic "topic-name"
---

# Video Design Specification Generation Workflow

Generate Video Design Specifications using the three-part workflow that separates deterministic operations from LLM generation.

## Implementation Steps

Step 1: **Execute Pre-Processing**
   - Run the command below to execute the pre-processing script adapted for single video workflow
   ```bash
   python scripts/claude_cli/content_video_design/pre_process.py --topic "{topic}"
   ```

Step 2: **Read Scene Count and Trigger LLM Generation**
   - Get metadata path by running:
```bash
python .claude/skills/video-creator/scripts/path_manager.py --topic "{topic}" --asset-type "Design" --subpath "metadata" --quiet
```
   - Read the file path returned to get scene count from <total_scenes> as S

Step 3: **Execute Scene Design Generation for All Scenes**
   - Run the `content_scene_design_generator` agent using the Task tool for every scene index
   - Execute all scene generation agents in parallel (do not run in background) and pass scene index as --scene S
   - run the agents for 0 till S-1 values 

Step 4: **Execute Post-Processing**
   - Run the command
   ```bash
   python scripts/claude_cli/content_video_design/post_process.py --topic "{topic}"
   ```