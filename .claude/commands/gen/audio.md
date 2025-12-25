---
description: Generate audio from video script by invoking the video-creator skill.
allowed-tools: Skill
model: haiku
argument-hint: --topic "topic-name"
---

# Audio Generation

Invoke the video-creator skill:

```
Skill: video-creator

Execute Mode: Single Step Execution
- Step: audio
- Topic: {topic}
```