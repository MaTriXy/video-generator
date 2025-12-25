# Audio Generation Step

Generates audio from the video script using text-to-speech.

## Execute

### Initial Generation (v3 Model)

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



