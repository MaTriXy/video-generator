# Bezier Path

**Use Case:** Custom cubic bezier

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `cp1_x` | First control point X |
| `cp1_y` | First control point Y |
| `cp2_x` | Second control point X |
| `cp2_y` | Second control point Y |
| `end_x` | Ending X coordinate |
| `end_y` | Ending Y coordinate |

## Example - Custom curve with control points

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" bezier --params '{"start_x": 100, "start_y": 400, "cp1_x": 200, "cp1_y": 100, "cp2_x": 600, "cp2_y": 100, "end_x": 700, "end_y": 400}'
```
