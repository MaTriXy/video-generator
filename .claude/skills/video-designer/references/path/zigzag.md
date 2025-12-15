# Zigzag Path

Sharp angular back-and-forth pattern.

## Use Cases
- Lightning
- Sharp turns
- Jagged paths

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_x` | number | Yes | Starting X coordinate |
| `start_y` | number | Yes | Starting Y coordinate |
| `segment_length` | number | Yes | Length of each diagonal segment |
| `amplitude` | number | Yes | Width of zigzag from center line |
| `segments` | number | Yes | Number of zigzag segments |

## path_params

```json
"path_params": {
  "type": "zigzag",
  "start_x": 100,
  "start_y": 300,
  "segment_length": 50,
  "amplitude": 80,
  "segments": 8
}
```
