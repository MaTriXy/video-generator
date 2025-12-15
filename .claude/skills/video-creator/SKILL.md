---
name: video-creator
description: Orchestrates video creation workflow with resumable status tracking
---

# Create Video Skill

Orchestrates the complete video creation workflow with status tracking.

## Parameters

- `topic` (optional): Video topic name

## Workflow

### Initialization

**If topic NOT provided:**
1. Read and execute: [user-input.md](./references/user-input.md)
2. Get `topic` from step 1 execution
3. Create status file:
   ```bash
   python .claude/skills/video-creator/scripts/video-status-file-manager.py --action create-video-status-file --topic "{topic}"
   ```

**If topic provided:**
1. Check if status file exists:
   ```bash
   python .claude/skills/video-creator/scripts/video-status-file-manager.py --action check-if-file-exist --topic "{topic}"
   ```
2. If returns error: **STOP** and tell user "Topic '{topic}' does not exist. Please create a new video without providing a topic."

### Step Execution Loop

Repeat until all steps completed:

1. **Get Next Step:**
   ```bash
   python .claude/skills/video-creator/scripts/video-status-file-manager.py --action get-next-step --topic "{topic}"
   ```

   Returns either:
   ```json
   {
     "step_id": "audio",
   }
   ```
   OR:
   ```json
   {"completed": true, "message": "All steps completed"}
   ```

2. **If completed=true:** Exit loop and show completion message

3. **Otherwise:**
   - Read and execute the instructions from the step referenced by `step_id` (see Step References section below)
   - Mark step complete:
     ```bash
     python .claude/skills/video-creator/scripts/video-status-file-manager.py --action complete-step --topic "{topic}" --step "{step_id}"
     ```

4. **Repeat**

### Completion

Display: "Hurray your video is ready now"

## Step References

**Note:** Only read these files when instructed by the Step Execution Loop above.

- [user-input.md](./references/user-input.md) - Gather topic and video style
- [audio.md](./references/audio.md) - Generate audio from script
- [direction.md](./references/direction.md) - Create video direction
- [asset-generator.md](./references/asset-generator.md) - Generate SVG assets
- [design.md](./references/design.md) - Generate design specifications
- [coding.md](./references/coding.md) - Create video components
