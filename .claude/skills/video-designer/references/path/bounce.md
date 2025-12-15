# Bounce Path

Bouncing trajectory with decreasing height.

## Use Cases
- Ball bouncing
- Hopping motion
- Rebounding objects

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_x` | number | Yes | Starting X coordinate |
| `start_y` | number | Yes | Starting Y coordinate |
| `end_x` | number | Yes | Ending X coordinate |
| `ground_y` | number | Yes | Y-coordinate of ground/floor |
| `initial_height` | number | Yes | Height of first bounce |
| `bounces` | number | Yes | Number of bounces |
| `decay` | number | No | Height reduction factor per bounce (default 0.6) |

## path_params

```json
"path_params": {
  "type": "bounce",
  "start_x": 100,
  "start_y": 100,
  "end_x": 700,
  "ground_y": 400,
  "initial_height": 250,
  "bounces": 4,
  "decay": 0.6
}
```
