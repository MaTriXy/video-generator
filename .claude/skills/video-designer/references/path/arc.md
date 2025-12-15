# Arc Path

Single curved arc segment.

## Use Cases
- Door swings
- Partial circles
- Simple curves

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_x` | number | Yes | Starting X coordinate |
| `start_y` | number | Yes | Starting Y coordinate |
| `end_x` | number | Yes | Ending X coordinate |
| `end_y` | number | Yes | Ending Y coordinate |
| `radius` | number | Yes | Arc radius in pixels |
| `sweep` | number | No | 1 for clockwise, 0 for counter-clockwise (default 1) |
| `large_arc` | number | No | 1 for arc > 180°, 0 for arc < 180° (default 0) |

## path_params

```json
"path_params": {
  "type": "arc",
  "start_x": 100,
  "start_y": 300,
  "end_x": 400,
  "end_y": 300,
  "radius": 200,
  "sweep": 1,
  "large_arc": 0
}
```
