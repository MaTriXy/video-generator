---
description: generate React video component by following the instructions given below.
allowed-tools: Bash, Task
model: sonnet
argument-hint: --topic "topic-name"
---

Step 1: **Run the pre-processing script**
- Execute the pre-processing script adapted for single video workflow:
```bash
python scripts/claude_cli/content_video/pre_process.py --topic "{topic}"
```

Step 2: **Read Scene Count**
   - Get metadata path by running:
```bash
python .claude/skills/video-creator/scripts/path_manager.py --topic "{topic}" --asset-type "Video" --subpath "metadata" --quiet
```
   - Read the file path returned and extract <total_scenes> as S

Step 3: **Execute Scene Generation**
   - Run the **content_scene_generator** agent using the Task tool for every scene from 0 to S-1 parallely (do not run in background)
   - pass --topic "{topic}" --scene S to the agent

Step 4: **Execute Post-Processing**
   - Run the post-processing script adapted for single video workflow:
```bash
python scripts/claude_cli/content_video/post_process.py --topic "{topic}"
```