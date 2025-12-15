# Arc Path

**Use Case:** Single arc segment

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `end_x` | Ending X coordinate |
| `end_y` | Ending Y coordinate |
| `radius` | Radius of the arc |

## Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `sweep` | Direction (0 = counter-clockwise, 1 = clockwise) | 1 |
| `large_arc` | Use larger arc (0 = smaller, 1 = larger) | 0 |

## Example - Door swinging open

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" arc --params '{"start_x": 100, "start_y": 300, "end_x": 400, "end_y": 300, "radius": 200, "sweep": 1, "large_arc": 0}'
```
