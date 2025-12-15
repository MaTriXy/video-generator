# Spline Path

Smooth curve that passes through multiple control points.

## Use Cases
- River flowing through landscape
- Organic curves
- Multi-point smooth paths
- Natural flowing motion

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `points` | array | Yes | Array of [x, y] coordinate pairs to pass through |
| `tension` | number | No | Controls curve tightness, 0-1 (default 0.3) |

## path_params

```json
"path_params": {
  "type": "spline",
  "points": [[100,300], [200,100], [300,350], [400,150], [500,300], [600,100], [700,250]],
  "tension": 0.3
}
```
