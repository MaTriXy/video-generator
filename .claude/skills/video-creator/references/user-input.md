## 1. Ask for Video Style

Use AskUserQuestion with these options:

{
  questions: [{
    question: "Which video style do you prefer?",
    header: "Video Style",
    multiSelect: false,
    options: [
      {
        label: "Pencil",
        description: "Pencil Style"
      },
      {
        label: "Infographic",
        description: "Infographic Style"
      },
      {
        label: "Neon",
        description: "Neon Style"
      }
    ]
  }]
}


## 2. Ask for Script and Validate (Loop Until Valid)

Repeat the following until script is valid:

a. Ask user directly (NOT using AskUserQuestion tool): "Please provide your video script (maximum 2000 characters):"
   - User will paste their script as plain text

b. Generate topic name from script (2-3 words):
   - Extract meaningful words from script (3+ characters, lowercase)
   - Join with hyphens
   - Append 3-4 random alphanumeric characters for uniqueness (e.g., "quantum-computing-basics-a7x2")

c. Get script file path by running:
```bash
python .claude/skills/video-creator/scripts/path_manager.py --topic "{generated_topic}" --asset-type "Scripts" --subpath "script-file" --quiet
```

d. Save script directly:
   - Write script to the path returned by the above command

e. Run post-process script:
```bash
python scripts/claude_cli/create_video_user_input/post_process.py --topic "{generated_topic}" --video-style "{user_selected_style_label}"
```

f. Parse the JSON output and check the `message` field and do the action if needed

## Output

Return to orchestrator with:
- `topic`: The generated topic name (e.g., "quantum-computing-basics")

