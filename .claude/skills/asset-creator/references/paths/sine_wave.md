# Sine Wave Path

**Use Case:** Waves, snake movement

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `start_x` | Starting X coordinate |
| `start_y` | Starting Y coordinate |
| `wavelength` | Length of one wave cycle |
| `amplitude` | Height of the wave |
| `cycles` | Number of wave cycles |

## Example - Snake slithering

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" sine_wave --params '{"start_x": 50, "start_y": 300, "wavelength": 100, "amplitude": 60, "cycles": 6}'
```
