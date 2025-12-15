# S-Curve Path

**Use Case:** Smooth transitions

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `end_x` | Ending X coordinate |
| `end_y` | Ending Y coordinate |

## Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `curvature` | Amount of curve (0-1) | 0.5 |

## Example - Road winding through hills

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" s_curve --params '{"start_x": 100, "start_y": 200, "end_x": 700, "end_y": 500, "curvature": 0.4}'
```
