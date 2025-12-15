# Linear Path

**Use Case:** Straight line A→B

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `end_x` | Ending X coordinate |
| `end_y` | Ending Y coordinate |

## Example - Laser beam

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" linear --params '{"start_x": 100, "start_y": 100, "end_x": 700, "end_y": 400}'
```
