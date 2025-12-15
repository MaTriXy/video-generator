## 1. Pre-Processing

Execute:
```bash
python scripts/claude_cli/content_video_design/pre_process.py --topic "{topic}"
```

## 2. Read Scene Count

Get metadata path by running:
```bash
python .claude/skills/video-creator/scripts/path_manager.py --topic "{topic}" --asset-type "Design" --subpath "metadata" --quiet
```
Read the file path returned and extract: total_scenes as S

## 3. Generate Scene Designs (Parallel)

For each scene from 0 to S-1, invoke the content_scene_design_generator agent in parallel:

```
Task (parallel): content_scene_design_generator agent with --topic "{topic}" --scene {scene_index}
```

Execute all scene generation agents in a single message (parallel execution).

## 4. Post-Processing

Execute:
```bash
python scripts/claude_cli/content_video_design/post_process.py --topic "{topic}"
```
