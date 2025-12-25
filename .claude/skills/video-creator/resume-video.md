# Resume Video

Resume video generation for an existing topic by continuing from the last completed step.

## Workflow

If the user has not provided a topic name, ask them to specify which topic they want to work with.

### 1. Get Next Step

Get the next pending step:

```bash
python .claude/skills/video-creator/scripts/video-status.py --action "get-incomplete-step" --topic <topic>
```

**Handle response:**
- If starts with `ERROR: Topic`:
  - Ask user for another topic as the provided topic status file does not exist.
- The response will contain the step id to execute.

### 2. Step Execution Loop

Repeat this loop until all steps are completed:

**Step A: Execute step instructions**

Read and follow the instructions from the step file for the current step id.

**Step B: Mark step complete**
```bash
python .claude/skills/video-creator/scripts/video-status.py --action "complete-step" --topic <topic> --step <step_id>
```

**Step C: Handle response**

The response will contain the next step id to execute. Return to Step A with the new step id.

