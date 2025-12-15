# SVG Fundamentals

## Basic SVG Structure

```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <style>
    /* CSS styles and animations */
  </style>

  <!-- SVG elements here -->
</svg>
```

### Root Element Attributes

| Attribute | Purpose | Example |
|-----------|---------|---------|
| `viewBox` | Internal coordinate system | `"0 0 100 100"` |
| `xmlns` | XML namespace (required) | `"http://www.w3.org/2000/svg"` |

For detailed viewBox sizing and positioning, see [viewbox-positioning.md](./references/viewbox-positioning.md).

---

## Basic Shapes

### Rectangle

```svg
<rect x="10" y="10" width="80" height="60" rx="5" ry="5" fill="#3B82F6"/>
```

| Attribute | Purpose |
|-----------|---------|
| `x`, `y` | Position (top-left corner) |
| `width`, `height` | Dimensions |
| `rx`, `ry` | Corner radius |
| `fill` | Fill color |

### Circle

```svg
<circle cx="50" cy="50" r="40" fill="#EF4444"/>
```

| Attribute | Purpose |
|-----------|---------|
| `cx`, `cy` | Center position |
| `r` | Radius |

### Ellipse

```svg
<ellipse cx="50" cy="50" rx="40" ry="25" fill="#10B981"/>
```

| Attribute | Purpose |
|-----------|---------|
| `cx`, `cy` | Center position |
| `rx`, `ry` | X and Y radii |

### Line

```svg
<line x1="10" y1="10" x2="90" y2="90" stroke="#000" stroke-width="2"/>
```

### Polyline (open shape)

```svg
<polyline points="10,90 50,10 90,90" fill="none" stroke="#000" stroke-width="2"/>
```

### Polygon (closed shape)

```svg
<polygon points="50,10 90,90 10,90" fill="#F59E0B"/>
```

---

## Path Element

The `<path>` element is the most powerful SVG element, using commands to draw complex shapes.

### Path Commands

| Command | Name | Parameters | Example |
|---------|------|------------|---------|
| `M` | Move to | x, y | `M 10 10` |
| `L` | Line to | x, y | `L 90 90` |
| `H` | Horizontal line | x | `H 50` |
| `V` | Vertical line | y | `V 50` |
| `C` | Cubic Bezier | x1,y1 x2,y2 x,y | `C 20,20 80,20 90,90` |
| `Q` | Quadratic Bezier | x1,y1 x,y | `Q 50,0 90,90` |
| `A` | Arc | rx ry rotation large-arc sweep x y | `A 25 25 0 0 1 50 50` |
| `Z` | Close path | - | `Z` |

Lowercase commands use relative coordinates (relative to current position).

### Example Path

```svg
<!-- Triangle -->
<path d="M 50 10 L 90 90 L 10 90 Z" fill="#8B5CF6"/>

<!-- Curved shape -->
<path d="M 10 50 Q 50 10 90 50 T 170 50" stroke="#000" fill="none"/>
```

---

## Groups and Transforms

### Group Element

Use `<g>` to group elements and apply shared transforms or styles:

```svg
<g transform="translate(50, 50)" fill="#3B82F6">
  <circle r="20"/>
  <rect x="-10" y="25" width="20" height="10"/>
</g>
```

### Transform Attribute

| Transform | Syntax | Example |
|-----------|--------|---------|
| Translate | `translate(x, y)` | `translate(50, 50)` |
| Scale | `scale(s)` or `scale(sx, sy)` | `scale(2)` |
| Rotate | `rotate(deg)` or `rotate(deg, cx, cy)` | `rotate(45)` |
| Skew | `skewX(deg)` or `skewY(deg)` | `skewX(10)` |

For detailed transform patterns and icon positioning, see [viewbox-positioning.md](./references/viewbox-positioning.md).

---

## Styling

### Fill and Stroke

```svg
<rect
  fill="#3B82F6"           /* Fill color */
  fill-opacity="0.8"       /* Fill transparency */
  stroke="#1D4ED8"         /* Stroke color */
  stroke-width="2"         /* Stroke width */
  stroke-opacity="0.9"     /* Stroke transparency */
  stroke-linecap="round"   /* Line end style: butt | round | square */
  stroke-linejoin="round"  /* Corner style: miter | round | bevel */
  stroke-dasharray="5 3"   /* Dash pattern */
/>
```

### Colors

```svg
fill="#3B82F6"           /* Hex */
fill="rgb(59, 130, 246)" /* RGB */
fill="rgba(59, 130, 246, 0.5)" /* RGBA */
fill="currentColor"      /* Inherit from parent */
fill="none"              /* Transparent */
```

### Embedded CSS

```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <style>
    .primary { fill: #3B82F6; }
    .secondary { fill: #EF4444; }
    .outline { fill: none; stroke: #000; stroke-width: 2; }
  </style>

  <circle class="primary" cx="50" cy="50" r="30"/>
</svg>
```
---

## Definitions and Reuse

### Defs Element

Store reusable elements that won't render directly:

```svg
<defs>
  <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#3B82F6"/>
    <stop offset="100%" stop-color="#8B5CF6"/>
  </linearGradient>
</defs>

<rect fill="url(#grad1)" x="10" y="10" width="80" height="80"/>
```
### Transform Attribute

| Transform | Syntax | Example |
|-----------|--------|---------|
| Translate | `translate(x, y)` | `translate(50, 50)` |
| Scale | `scale(s)` or `scale(sx, sy)` | `scale(2)` |
| Rotate | `rotate(deg)` or `rotate(deg, cx, cy)` | `rotate(45)` |
| Skew | `skewX(deg)` or `skewY(deg)` | `skewX(10)` |

### Use Element

Reference defined elements:

```svg
<defs>
  <circle id="dot" r="5"/>
</defs>

<use href="#dot" x="20" y="20" fill="red"/>
<use href="#dot" x="50" y="50" fill="blue"/>
<use href="#dot" x="80" y="80" fill="green"/>
```

---

## Gradients

### Linear Gradient

```svg
<defs>
  <linearGradient id="linear" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#3B82F6"/>
    <stop offset="100%" stop-color="#EF4444"/>
  </linearGradient>
</defs>
```

### Radial Gradient

```svg
<defs>
  <radialGradient id="radial" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#FFF"/>
    <stop offset="100%" stop-color="#3B82F6"/>
  </radialGradient>
</defs>
```

---

## Clipping and Masking

### Clip Path

```svg
<defs>
  <clipPath id="circle-clip">
    <circle cx="50" cy="50" r="40"/>
  </clipPath>
</defs>

<rect clip-path="url(#circle-clip)" x="0" y="0" width="100" height="100" fill="#3B82F6"/>
```

### Mask

```svg
<defs>
  <mask id="fade-mask">
    <linearGradient id="fade" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="white"/>
      <stop offset="100%" stop-color="black"/>
    </linearGradient>
    <rect fill="url(#fade)" width="100" height="100"/>
  </mask>
</defs>

<rect mask="url(#fade-mask)" fill="#3B82F6" width="100" height="100"/>
```

---

## Best Practices

1. **Always use viewBox** - Enables proper scaling
2. **Use transparent background** - No background rect unless needed
3. **Group related elements** - Use `<g>` for organization and shared transforms
4. **Use meaningful IDs** - For gradients, clips, and reusable elements
5. **Optimize paths** - Remove unnecessary precision (2 decimal places max)
6. **Use classes for styling** - Separate presentation from structure