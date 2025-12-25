# Create Video

Create a complete video from scratch, starting from script input through final component generation.

## Workflow

### 1. User Input

Follow instructions in [user-input-step.md](./steps/user-input-step.md)

### 2. Initialize Status Tracking and Get First Step

Create status tracking file and get the first step to execute:
```bash
python .claude/skills/video-creator/scripts/video-status.py --action "create-video-status-file" --topic <topic>
```

The response will contain the step id to execute.

### 3. Step Execution Loop

Repeat this loop until all steps are completed:

**Step A: Execute step instructions**

Read and follow the instructions from the step file for the current step id.

**Step B: Mark step complete and get next step**
```bash
python .claude/skills/video-creator/scripts/video-status.py --action "complete-step" --topic <topic> --step <step_id>
```

The response will contain the next step id to execute. Return to Step A with the new step id.