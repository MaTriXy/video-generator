# Sine Wave Path

Smooth oscillating wave pattern.

## Use Cases
- Snake movement
- Water waves
- Oscillations

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_x` | number | Yes | Starting X coordinate |
| `start_y` | number | Yes | Starting Y coordinate |
| `wavelength` | number | Yes | Distance for one complete wave cycle |
| `amplitude` | number | Yes | Height of wave peaks from center line |
| `cycles` | number | Yes | Number of complete wave cycles |

## path_params

```json
"path_params": {
  "type": "sine_wave",
  "start_x": 50,
  "start_y": 300,
  "wavelength": 100,
  "amplitude": 60,
  "cycles": 6
}
```
