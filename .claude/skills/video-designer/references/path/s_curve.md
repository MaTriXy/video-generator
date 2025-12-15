# S-Curve Path

Smooth S-shaped transition between two points.

## Use Cases
- Winding roads
- Smooth directional changes
- Flowing transitions

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_x` | number | Yes | Starting X coordinate |
| `start_y` | number | Yes | Starting Y coordinate |
| `end_x` | number | Yes | Ending X coordinate |
| `end_y` | number | Yes | Ending Y coordinate |
| `curvature` | number | No | Bend intensity, range 0-1 (default 0.5) |

## path_params

```json
"path_params": {
  "type": "s_curve",
  "start_x": 100,
  "start_y": 200,
  "end_x": 700,
  "end_y": 500,
  "curvature": 0.4
}
```
