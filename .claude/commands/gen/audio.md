---
description: generate audio from video script using ElevenLabs
allowed-tools: Bash
model: haiku
argument-hint: --topic "topic-name"
---

## Audio Generation

Run the audio content post-processor to generate audio from the video script:

```bash
python scripts/claude_cli/content_audio/post_process.py --topic "{topic}"
```
