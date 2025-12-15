# Elliptical Path

**Use Case:** Oval orbits

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `center_x` | Center X coordinate |
| `center_y` | Center Y coordinate |
| `radius_x` | Horizontal radius |
| `radius_y` | Vertical radius |

## Example - Comet orbit

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" elliptical --params '{"center_x": 400, "center_y": 300, "radius_x": 200, "radius_y": 100}'
```
