# User Input Step

Gathers video script and style preferences from the user.

## Step 1: Collect Video Style

Use the AskUserQuestion tool with these parameters:

```javascript
{
  questions: [{
    question: "Which video style do you prefer?",
    header: "Video Style",
    multiSelect: false,
    options: [
      {
        label: "Pencil",
        description: "Hand-drawn pencil sketch aesthetic"
      },
      {
        label: "Infographic",
        description: "Clean, modern infographic style"
      },
      {
        label: "Neon",
        description: "Vibrant neon-lit visual style"
      }
    ]
  }]
}
```

## Step 2: Collect Script

**A. Prompt for script**

Ask user directly (do NOT use AskUserQuestion tool):

```
Please provide your video script (maximum 2000 characters):
```

User will paste their script as plain text.

**B. Generate unique topic identifier**

Create a topic name from the script:
1. Extract meaningful 2 words from script (3+ characters, lowercase)
2. Join words with hyphens
3. Append 4 random alphanumeric characters for uniqueness

Example: "quantum-computing-a7x2"

**C. Save script to file**

1. **Get Script File Path**: Run bash command to get the script file path:
```bash
python .claude/skills/video-creator/scripts/path_manager.py --topic <topic> --asset-type "Scripts" --subpath "script-file"
```

2. **Write Script**: Write the user's script to the path returned by the above command.

**D. Validate script**

Run validation:
```bash
python scripts/claude_cli/create_video_user_input/post_process.py --topic <topic> --video-style <video_style>
```

Check the output:
- If output starts with `ERROR:`: Show the error message to user and ask again only for the script or video style input that failed validation

**E. Generate script with emotion tags**

After validation passes, invoke the audio-tags agent to add ElevenLabs emotion tags to the script.

Invoke the audio-tags agent using Task tool with `--topic <topic>`: (do not run in background)

Wait for the agent to complete before proceeding.