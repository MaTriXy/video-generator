## Path Creation Guidelines

To design a path you need to use the following schemas so that a path is precisely created.

To use path an element should set "type" of the element as "path".

### **Path Types**

| Type | Description | Reference |
|------|-------------|-----------|
| `arc` | Single curved arc segment for door swings, partial circles | [arc.md](./references/path/arc.md) |
| `bezier` | Custom cubic bezier with two control points for flowing curves | [bezier.md](./references/path/bezier.md) |
| `bounce` | Bouncing trajectory with decreasing height for ball physics | [bounce.md](./references/path/bounce.md) |
| `circular` | Complete circle around a center point for orbits, spinning | [circular.md](./references/path/circular.md) |
| `elliptical` | Oval-shaped closed path for stretched orbits | [elliptical.md](./references/path/elliptical.md) |
| `linear` | Straight line A-B for laser beams, direct arrows | [linear.md](./references/path/linear.md) |
| `parabolic` | Arc that rises then falls for projectiles, jumps | [parabolic.md](./references/path/parabolic.md) |
| `s_curve` | Smooth S-shaped transition for winding roads | [s_curve.md](./references/path/s_curve.md) |
| `sine_wave` | Smooth oscillating wave for snake movement, water | [sine_wave.md](./references/path/sine_wave.md) |
| `spiral` | Inward/outward spiral for tornado, galaxy, swirls | [spiral.md](./references/path/spiral.md) |
| `spline` | Smooth curve through multiple points for organic paths | [spline.md](./references/path/spline.md) |
| `zigzag` | Sharp angular back-and-forth for lightning, jagged paths | [zigzag.md](./references/path/zigzag.md) |

### **Coordinate System**

- Origin (0,0) at top-left
- X increases right, Y increases down

---

## Arrow Marker

  Arrow markers place an arrowhead at the end of a path. Three visual styles are available: `hollow` (outlined arrowhead), `fill` (filled arrowhead), and `line` (simple line arrow).

### Arrow Marker Schema Example

```json
{
 "path_params":
    {
      "type": "linear",
      "start_x": 0,
      "start_y": 0,
      "end_x": 200,
      "end_y": 0
    },
 "arrow_marker": "hollow|fill|line", //(optional field)
}
```

## Path Animation Types

### Entrance Animations

| Animation | Description |
|-----------|-------------|
| `path-draw` | Progressively draws the path from start to end over the specified duration


### Exit Animations
| Animation | Description |
|-----------|-------------|
| `path-erase` | Progressively erases the path from start to end |

### Path-Draw Animation

The `path-draw` animation is specifically designed for path elements. It draws the path progressively over the specified duration, creating a "drawing" effect.

This will draw the path over 1000ms (1 second), starting from the path's origin and following its defined trajectory.

## Composite Paths (Multiple Path Segments)

To create a single path element that comprises multiple connected path segments, use `merge_path_params` instead of `path_params`. The `merge_path_params` is an **array** of path configurations where each segment defines its own path type and parameters. They are drawn sequentially to form one continuous composite path. The start of the second path will be from teh end of the previous path.

### Composite/Merged Path Schema

```json
{
  "id": "composite_path_id",
  "type": "path",
  "content": "A composite path combining multiple segments",
  "zIndex": 1,

  "timing": {
    "enterOn": 0,
    "exitOn": 5000
  },

  // IMPORTANT: All timing values (enterOn, exitOn, action.on) must use absolute video timestamps
  // matching scene.startTime, not relative scene time. If syncing to audio at relative time T,
  // use: scene.startTime + T

  "merge_path_params": [
    {
      "type": "linear",
      "start_x": 0,
      "start_y": 0,
      "end_x": 200,
      "end_y": 0
    },
    {
      "type": "arc",
      "start_x": 200,
      "start_y": 0,
      "end_x": 200,
      "end_y": 100,
      "radius": 50,
      "sweep": 1,
      "large_arc": 0
    },
    {
      "type": "linear",
      "start_x": 200,
      "start_y": 100,
      "end_x": 0,
      "end_y": 100
    }
  ],

  "animation": {
    "entrance": {
      "type": "path-draw",
      "duration": 1500
    }
  },
  "styles": {
    "position": { "x": 400, "y": 300 },
    "size": { "width": 250, "height": 150 },
    "states": {
      "default": {
        "stroke": "#FF5722",
        "strokeWidth": 4,
        "fill": "none"
      }
    }
  }
}
```

### Key Points for Composite Paths

1. **Use `merge_path_params`**: Use this instead of `path_params` when you need to combine multiple path segments
2. **Array Format**: `merge_path_params` is always an array where each element defines a separate path segment
3. **Sequential Connection**: Segments are drawn in order; ensure the `end` of one segment matches the `start` of the next for smooth connections
4. **Mixed Types**: You can combine any path types (linear, arc, bezier, parabolic, etc.) within a single composite path
5. **Single Animation**: The entire composite path shares one animation configuration - `path-draw` will draw all segments sequentially
6. **Unified Styling**: All segments inherit the same stroke, fill, and style properties from the parent element

---

## Path Element Schema

When creating a path element, use `type: "path"` and include `path_params` to define the path geometry.

```json
{
  "id": "unique_path_id",
  "type": "path",
  "content": "Description of the path - e.g., 'a parabolic path to show a trijectory of a missile'",
  "zIndex": 1,

  "timing": {
    "enterOn": 0,
    "exitOn": 5000
  },

  // IMPORTANT: All timing values (enterOn, exitOn, action.on) must use absolute video timestamps
  // matching scene.startTime, not relative scene time. If syncing to audio at relative time T,
  // use: scene.startTime + T

  "path_params": {
    "type": "linear|arc|bezier|bounce|circular|elliptical|parabolic|s_curve|sine_wave|spiral|spline|zigzag",
    // ... type-specific parameters (see individual path reference files)
  },

  "animation": {
    "entrance": {
      "type": "path-draw or any other entrance animation",
      "duration": 800
    },
    "exit": {
      "type": "path-erase or any other exit animation",
      "duration": 300
    },
    "actions": []
  },
  "styles": {
    "position": {
      "x": 960,
      "y": 540
    },
    "size": {
      "width": 400,
      "height": 200
    },
    "states": {
      "default": {
        "stroke": "#FFFFFF",
        "strokeWidth": 3,
        "fill": "none",
        "opacity": 1
      }
    }
  }
}
```
