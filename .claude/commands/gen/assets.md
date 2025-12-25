---
description: Generate SVG assets from Direction requirements by invoking the video-creator skill.
allowed-tools: Skill
model: inherit
argument-hint: --topic "topic-name"
---

# Asset Generation

Invoke the video-creator skill:

```
Skill: video-creator

Execute Mode : Single Step Execution
- Step: asset-generator
- Topic: {topic}
```
