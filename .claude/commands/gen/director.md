---
description: generate video direction by following the instructions given below.
allowed-tools: Task, SlashCommand
model: sonnet
argument-hint: --topic "topic-name"
---

# Content Video Direction Generation Workflow

Generate a video direction using the three-part workflow that separates deterministic operations from LLM generation

## Implementation Steps

### PHASE 1: Direction Generation

Step 1: **Run the direction pre-processing script**
- Execute the pre-processing script adapted for single video workflow:
```bash
python scripts/claude_cli/content_video_direction/pre_process.py --topic "{topic}"
```

Step 2: **Execute LLM Generation**
   - Use the Task tool to invoke the content_video_direction_generator sub-agent with --topic "{topic}"

Step 3: **Execute Direction Post-Processing**
   - Run the post-processing script adapted for single video workflow:
```bash
python scripts/claude_cli/content_video_direction/post_process.py --topic "{topic}"
```

## Error Handling
- If direction generation fails after retries: Display error and abort workflow
- If post-processing fails: Display error but keep generated result for debugging
- If script prerequisite not completed: Display error indicating required workflow order


