# Bounce Path

**Use Case:** Bouncing ball trajectory

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `end_x` | Ending X coordinate |
| `ground_y` | Y coordinate of the ground |
| `initial_height` | Height of first bounce |
| `bounces` | Number of bounces |

## Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `decay` | Height reduction per bounce (0-1) | 0.6 |

## Example - Ball bouncing across screen

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" bounce --params '{"start_x": 100, "start_y": 100, "end_x": 700, "ground_y": 400, "initial_height": 250, "bounces": 4, "decay": 0.6}'
```
