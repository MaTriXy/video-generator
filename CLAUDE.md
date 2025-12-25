
# Project Instructions

**IMPORTANT:** No matter what the question is , invoke this skill as soon as file is loaded.

```
Skill: video-creator
```

Do NOT proceed with any other actions until the skill is invoked.

## Edit Tool Policy

When a file is written by any agent during the current session, it does not need to be read before applying the Edit tool. The agent already has context of the file contents from writing it.

## File Verification Policy

**⚠️ IMPORTANT:** Do NOT read files back to verify they were saved after writing. Trust the write operation. Any necessary validation will be handled by downstream processes automatically. This reduces unnecessary token consumption.

## Agent Output Format

**⚠️ CRITICAL - MUST FOLLOW:** When a task is complete, output ONLY ONE single line. No explanations, no summaries, no verbose text. Just one clear line stating what was done.
Example: `✅ AGENT COMPLETED RUNNING Status: success/failure`