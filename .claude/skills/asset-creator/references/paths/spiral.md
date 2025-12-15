# Spiral Path

**Use Case:** Tornado, galaxy, swirls

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `center_x` | Center X coordinate |
| `center_y` | Center Y coordinate |
| `max_radius` | Maximum radius of the spiral |
| `revolutions` | Number of spiral turns |

## Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `points` | Number of points for smoothness | auto |

## Example - Water draining

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" spiral --params '{"center_x": 400, "center_y": 300, "max_radius": 150, "revolutions": 3}'
```
