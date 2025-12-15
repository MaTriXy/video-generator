# Spiral Path

Inward or outward spiral pattern.

## Use Cases
- Tornado
- Galaxy
- Swirls
- Draining effect

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `center_x` | number | Yes | Center X coordinate |
| `center_y` | number | Yes | Center Y coordinate |
| `max_radius` | number | Yes | Maximum radius at outermost point |
| `revolutions` | number | Yes | Number of complete rotations |
| `points` | number | No | Number of points for smoothness (default 100) |

## path_params

```json
"path_params": {
  "type": "spiral",
  "center_x": 400,
  "center_y": 300,
  "max_radius": 150,
  "revolutions": 3,
  "points": 100
}
```
