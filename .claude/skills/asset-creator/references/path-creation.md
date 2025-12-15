# Path Creation

Generate SVG path `d` attributes using the Python script:

Use the bash tool to call the python script below.

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" <equation> --params '<json_params>'
```

## Path Types

| Path Type | Use Case | Details |
|-----------|----------|---------|
| `parabolic` | Projectiles, jumps, throws | [parabolic.md](./references/paths/parabolic.md) |
| `circular` | Orbits, spinning | [circular.md](./references/paths/circular.md) |
| `elliptical` | Oval orbits | [elliptical.md](./references/paths/elliptical.md) |
| `sine_wave` | Waves, snake movement | [sine_wave.md](./references/paths/sine_wave.md) |
| `spiral` | Tornado, galaxy, swirls | [spiral.md](./references/paths/spiral.md) |
| `s_curve` | Smooth transitions | [s_curve.md](./references/paths/s_curve.md) |
| `linear` | Straight line A→B | [linear.md](./references/paths/linear.md) |
| `arc` | Single arc segment | [arc.md](./references/paths/arc.md) |
| `bezier` | Custom cubic bezier | [bezier.md](./references/paths/bezier.md) |
| `zigzag` | Sharp angular back-and-forth | [zigzag.md](./references/paths/zigzag.md) |
| `bounce` | Bouncing ball trajectory | [bounce.md](./references/paths/bounce.md) |
| `spline` | Smooth curve through N points | [spline.md](./references/paths/spline.md) |

---

## Merging Paths

Use `merge-paths.py` to combine multiple path strings into a single continuous path:

```bash
python ./scripts/merge-paths.py --paths '["M 50 400 L 150 100", "M 150 100 Q 250 400 350 250", "M 350 250 L 500 250"]'
```
**Output:**
```
M 50 400 L 150 100 Q 250 400 350 250 L 500 250
```

**Tip:** Ensure each segment's start point matches the previous segment's end point.

## Path Styles

### Dashed Path
Use `stroke-dasharray` with two values: dash length and gap length.
```svg
<path d="M 100 200 L 700 200" fill="none" stroke="#333" stroke-width="3" stroke-dasharray="20 10"/>
```

### Dotted Path
Use `stroke-dasharray` with small equal values and `stroke-linecap="round"`.
```svg
<path d="M 100 200 L 700 200" fill="none" stroke="#333" stroke-width="3" stroke-dasharray="1 10" stroke-linecap="round"/>
```

---

## Show/Hide Path

Use `opacity` to show or hide a path with animation.

### Hide Path (visible → invisible)
```svg
<path d="M 100 300 Q 400 100 700 300" fill="none" stroke="#333" stroke-width="3" opacity="1">
  <animate attributeName="opacity" from="1" to="0" dur="1s" fill="freeze"/>
</path>
```

### Show Path (invisible → visible)
```svg
<path d="M 100 300 Q 400 100 700 300" fill="none" stroke="#333" stroke-width="3" opacity="0">
  <animate attributeName="opacity" from="0" to="1" dur="1s" fill="freeze"/>
</path>
```

## Coordinate System

- Origin (0,0) at top-left of the svg
- X increases right, Y increases down
- Plan parameters within your viewBox dimensions

## Boundary Constraints

**All path points must stay within valid bounds:**
- No coordinate value should be negative (minimum is 0)
- X coordinates must not exceed the element's width
- Y coordinates must not exceed the element's height

## Other References
Use the generated path to make an object follow it: See [path-following.md](./references/animations/path-following.md)
Use the path drawing animations: See [path-drawing.md](./references/animations/path-drawing.md)
