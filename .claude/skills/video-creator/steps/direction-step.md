# Direction Creation Step

Creates scene-by-scene video direction from the script and audio.

## Step 1: Run the below commnand to get the starting step

```bash
python .claude/skills/video-creator/scripts/video-step-sub-status.py --command "get-next-step" --topic <topic> --asset-type "Direction"
```

## Step 2: Pre-Processing

```bash
python scripts/claude_cli/content_video_direction/pre_process.py --topic <topic>
```

## Step 3: Generate Direction

Invoke the content_video_direction_generator agent (do not run in background)

```
<invoke name="Task">
    <parameter name="subagent_type">content_video_direction_generator</parameter>
    <parameter name="prompt">Generate direction for: --topic <topic></parameter>
    <parameter name="description">Generate direction</parameter>
</invoke>
```

## Step 4: Post-Processing

```bash
python scripts/claude_cli/content_video_direction/post_process.py --topic <topic>
```
