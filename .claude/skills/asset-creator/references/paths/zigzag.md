# Zigzag Path

**Use Case:** Sharp angular back-and-forth

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `segment_length` | Length of each segment |
| `amplitude` | Width of zigzag |
| `segments` | Number of zigzag segments |

## Example - Lightning bolt

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" zigzag --params '{"start_x": 100, "start_y": 300, "segment_length": 50, "amplitude": 80, "segments": 8}'
```
