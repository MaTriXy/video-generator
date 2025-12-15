## 1. Pre-Processing

Execute:
```bash
python scripts/claude_cli/content_video_direction/pre_process.py --topic "{topic}"
```


## 2. LLM Generation

Invoke the content_video_direction_generator agent using the Task tool:

```
Task: content_video_direction_generator agent with --topic "{topic}"
```


## 3. Post-Processing

Execute:
```bash
python scripts/claude_cli/content_video_direction/post_process.py --topic "{topic}"
```
