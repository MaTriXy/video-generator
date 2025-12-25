# Video Component Coding Step

Generates React TSX components for each video scene.

## Step 1: Run the below commnand to get the starting step

```bash
python .claude/skills/video-creator/scripts/video-step-sub-status.py --command "get-next-step" --topic <topic> --asset-type "Video"
```

## Step 2: Pre-Processing

```bash
python scripts/claude_cli/content_video/pre_process.py --topic <topic>
```

## Step 3: Get Scene Count

Run bash command to get the total_scenes:
```bash
python .claude/skills/video-creator/scripts/get_video_step_metadata.py --topic <topic> --asset-type "Video"
```

## Step 4: Generate Video Components

Invoke the content_scene_generator agent for <total_scenes> number of times 

```
<invoke name="Task">
    <parameter name="subagent_type">content_scene_generator</parameter>
    <parameter name="prompt">Generate video scene for: --topic <topic></parameter>
</invoke>
```

**IMPORTANT**: 
1. Execute the first agent , wait for the first agent to complete and then invoke the remaining scene code agents in parallel for efficiency.
2. Never run the subagents in the background.

## Step 5: Post-Processing

```bash
python scripts/claude_cli/content_video/post_process.py --topic <topic>
```



