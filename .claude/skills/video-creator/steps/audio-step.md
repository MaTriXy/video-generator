# Audio Generation Step

Generates audio from the video script using text-to-speech.

## Step 1: Add Emotion Tags

Invoke the audio-tags agent to add emotion tags to the script

```
<invoke name="Task">
    <parameter name="subagent_type">audio-tags</parameter>
    <parameter name="prompt">Add emotion tags for: --topic <topic></parameter>
    <parameter name="description">Add emotion tags</parameter>
</invoke>
```

## Step 2: Generate Audio (v3 Model)

```bash
python scripts/claude_cli/content_audio/post_process.py --topic <topic>
```

### Fallback Handling

If the v3 model generation fails (status: "needs_fallback"), you MUST:

1. **Ask the user** using the AskUserQuestion tool whether to retry with the v2.5 fallback model
   - Note: v2.5 model does not support emotion tags, so it will use the original script without emotion tags

2. **If user approves**, execute the fallback command:
   ```bash
   python scripts/claude_cli/content_audio/post_process.py --topic <topic> --use-fallback
   ```

3. **If user declines**, stop the video generation completely and report the failure



