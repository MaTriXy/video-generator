# Parabolic Path

Arc that rises then falls (or vice versa).

## Use Cases
- Projectiles
- Thrown objects
- Jumping arcs

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_x` | number | Yes | Starting X coordinate |
| `start_y` | number | Yes | Starting Y coordinate |
| `end_x` | number | Yes | Ending X coordinate |
| `end_y` | number | Yes | Ending Y coordinate |
| `arc_height` | number | Yes | Height above the line between start and end (negative for downward arc) |

## path_params

```json
"path_params": {
  "type": "parabolic",
  "start_x": 100,
  "start_y": 400,
  "end_x": 700,
  "end_y": 400,
  "arc_height": 200
}
```
