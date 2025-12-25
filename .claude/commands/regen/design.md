---
description: Regenerate video design specifications for specific scenes by invoking the video-creator skill.
allowed-tools: Skill
model: inherit
argument-hint: --topic "topic-name" --scenes "0,2,3"
---

# Video Design Specification Regeneration

Invoke the video-creator skill:

```
Skill: video-creator

Execute Mode: Regenerate Step
- Step: design
- Topic: {topic}
- Scenes: {scenes}
```
