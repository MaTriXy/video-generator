# Regenerate Video Component Coding Step

Regenerates React TSX components for selected scenes only.

## Step 1: Pre-Processing

```bash
python scripts/claude_cli/content_video/regen_pre_process.py --topic <topic> --scenes <scene_indices>
```

## Step 2: Generate Video Components

For each scene index in the scenes list, invoke the content_scene_generator agent:

```
<invoke name="Task">
    <parameter name="subagent_type">content_scene_generator</parameter>
    <parameter name="prompt">Generate video scene for: --topic <topic> --scene <scene_index></parameter>
    <parameter name="description">Regenerate video scene <scene_index></parameter>
</invoke>
```

**IMPORTANT**:
1. Execute the first scene in the list in isolation, then run all remaining scene agents in parallel for efficiency.
2. Never run the subagents in the background.

## Step 3: Post-Processing

```bash
python scripts/claude_cli/content_video/regen_post_process.py --topic <topic> --scenes <scene_indices>
```
