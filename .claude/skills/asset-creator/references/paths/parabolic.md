# Parabolic Path

**Use Case:** Projectiles, jumps, throws

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `end_x` | Ending X coordinate |
| `end_y` | Ending Y coordinate |
| `arc_height` | Height of the arc (positive = up, negative = down) |

## Example - Ball thrown in arc

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" parabolic --params '{"start_x": 100, "start_y": 400, "end_x": 700, "end_y": 400, "arc_height": 200}'
```

**Output:**
```
M 100 400 Q 400.0 200.0 700 400
```
