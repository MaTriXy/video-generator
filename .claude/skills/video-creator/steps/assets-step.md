# Asset Generation Step

Generates SVG assets required by the video direction.

## Step 1: Run the below commnand to get the starting step

```bash
python .claude/skills/video-creator/scripts/video-step-sub-status.py --command "get-next-step" --topic <topic> --asset-type "Assets"
```

## Step 2: Pre-Processing

Extract required assets from direction:

```bash
python scripts/claude_cli/asset_generator/pre_process.py --topic <topic>
```

## Step 3: Generate Assets

Invoke the asset_generator agent (do not run in background)

```
<invoke name="Task">
    <parameter name="subagent_type">asset_generator</parameter>
    <parameter name="prompt">Generate assets for: --topic <topic></parameter>
    <parameter name="description">Generate assets</parameter>
</invoke>
```

## Step 4: Post-Processing

```bash
python scripts/claude_cli/asset_generator/post_process.py --topic <topic>
```


