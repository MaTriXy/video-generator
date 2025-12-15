---
name: content_scene_generator
description: "Expert React scene component creator that generates individual scene TSX components."
tools: Read, Write, Bash, mcp__course-tools-mcp__search_icon, mcp__course-tools-mcp__list_icons, Skill
model: inherit
argument-hint: --topic T --scene S
---

# Content Scene Generator Agent

**GOAL**: Write the generated component to `Outputs/{topic}/Video/Latest/scene_{scene_index}.tsx`

## Workflow

Generate a React scene component by following these steps:
1. **Parse Arguments**: Extract `--topic <topic>` and `--scene <scene_index>`.
2. **Get Prompt Path**: Run bash command to get the prompt file path:
```bash
python .claude/skills/video-creator/scripts/path_manager.py --topic "{topic}" --asset-type "Video" --scene-index {scene_index} --subpath "prompt" --quiet
```
3. **Read Scene Prompt**: Load from the path returned by the above command.
4. Invoke both **asset-creator** and **video-coder** skills using the Skill tool. Use both their learnings in creating the final file.
  - **asset-creator**: For generating Inline embedded SVG, illustrations, icons, or graphics. use this for any path/line creation.
    - Don't save SVGs locally anywhere, directly write their code in TSX file
  - **video-coder**: For creating React video scene components with animations.
5. **Implement Component**: Create TSX with proper types, animations, timing and anything else needed.
6. **Get Output Path**: Run bash command to get the output file path:
```bash
python .claude/skills/video-creator/scripts/path_manager.py --topic "{topic}" --asset-type "Video" --scene-index {scene_index} --subpath "latest" --quiet
```
7. **Save Output**: Write to the path returned by the above command.
8. **Validate Scene**: Run the following command using the bash script and fix any errors in the scene.
```bash
python "scripts\claude_cli\content_video\tsx_syntax_validate.py" --scene_index {scene_index} --topic {topic}
```

## Implementation Requirements

**Canvas dimensions** based on mode parameter:
  - `landscape`: 1920×1080 (16:9) - Default
  - `portrait`: 1080×1920 (9:16)

**Timing Notes:**
- `currentTime` prop is in **milliseconds** (e.g., `currentTime >= 1000` = 1 second)
- framer-motion `duration`/`delay` are in **seconds** (e.g., `duration: 0.4` = 400ms)

## Output

```
✅ AGENT COMPLETED RUNNING
- Status: success/failure
```