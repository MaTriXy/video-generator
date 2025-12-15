# ViewBox & Positioning Guide

## Understanding ViewBox

The `viewBox` attribute defines the internal coordinate system of an SVG:

```svg
<svg viewBox="minX minY width height" xmlns="http://www.w3.org/2000/svg">
```

| Parameter | Meaning |
|-----------|---------|
| `minX` | Left edge X coordinate (usually 0) |
| `minY` | Top edge Y coordinate (usually 0) |
| `width` | Internal width in SVG units |
| `height` | Internal height in SVG units |

---

## Choosing ViewBox Size

| Use Case | Recommended ViewBox | Why |
|----------|---------------------|-----|
| Simple icons | `0 0 100 100` | Easy math, percentage-based |
| Detailed illustrations | `0 0 200 200` or `0 0 500 500` | More precision for complex paths |
| Wide banners | `0 0 300 100` | 3:1 aspect ratio |
| Tall graphics | `0 0 100 200` | 1:2 aspect ratio |
| Video scenes (16:9) | `0 0 1920 1080` | Matches video dimensions |

**Guidelines:** Match aspect ratio to display context. Larger viewBox = more precision. Square viewBox works well for icons.

---

## Coordinate System

```
(0,0) ─────────────────────────► X (width)
  │
  │     (25%,25%)        (75%,25%)
  │        ●────────────────●
  │        │                │
  │        │   (50%,50%)    │
  │        │       ●        │
  │        │    center      │
  │        │                │
  │        ●────────────────●
  │     (25%,75%)        (75%,75%)
  │
  ▼
 Y (height)
```

| Position | Formula |
|----------|---------|
| Top-left | (0, 0) |
| Top-center | (width/2, 0) |
| Center | (width/2, height/2) |
| Bottom-center | (width/2, height) |

---

## Icon Transform Pattern

**The standard pattern for placing icons:**

```svg
<g transform="translate(targetX, targetY) scale(S) translate(-centerX, -centerY)">
  <!-- icon paths here -->
</g>
```

**Read right-to-left:**
1. `translate(-centerX, -centerY)` → Move icon center to origin
2. `scale(S)` → Scale the icon
3. `translate(targetX, targetY)` → Move to final position

### Icon Library Reference

| Library | ViewBox | Center Offset | Scale Formula |
|---------|---------|---------------|---------------|
| Bootstrap (Bs) | 16x16 | `translate(-8, -8)` | `desiredSize / 16` |
| Font Awesome (Fa) | 512x512 | `translate(-256, -256)` | `desiredSize / 512` |
| Game Icons (Gi) | 512x512 | `translate(-256, -256)` | `desiredSize / 512` |

### Examples

```svg
<!-- Bootstrap icon at center (50,50), size 50 units, scale: 50/16 = 3.125 -->
<g transform="translate(50, 50) scale(3.125) translate(-8, -8)">
  <path d="..." />
</g>

<!-- Game Icon at center (960,540), size 400 units, scale: 400/512 = 0.78 -->
<g transform="translate(960, 540) scale(0.78) translate(-256, -256)">
  <path d="..." />
</g>
```

---

## Multi-Icon Layouts

### Side-by-Side (30% and 70% of width)

```svg
<g transform="translate(W*0.3, H*0.5) scale(S) translate(-cx, -cy)">...</g>
<g transform="translate(W*0.7, H*0.5) scale(S) translate(-cx, -cy)">...</g>
```

### Grid Layout (2x2)

| Position | Coordinates |
|----------|-------------|
| Top-left | (25%, 25%) |
| Top-right | (75%, 25%) |
| Bottom-left | (25%, 75%) |
| Bottom-right | (75%, 75%) |

---

## Safe Zone & Maximum Scale

Keep icon centers within 10%-90% of viewBox to prevent clipping:

```
availableSpace = viewBoxSize * 0.8
maxScale = availableSpace / iconViewBoxSize
```

---

## Transparent Background

SVGs are transparent by default. To maintain transparency:
- Do NOT add background rectangles unless requested
- Do NOT set fill on root SVG
- Apply fill only to icon paths

---

## Aligning Effects to Icon Attachment Points

When adding effects (muzzle flash, sparks, etc.) to specific points on an icon, calculate the exact position mathematically.

### Calculation Process

1. **Find attachment point in original icon space** (e.g., gun barrel tip at (486, 175) in 512x512)
2. **Apply transforms in order** (right-to-left)
3. **Position effect at calculated point**

### Example: Gun Barrel at (486, 175), icon placed at (25, 50) with scale 0.12

```
Step 1 - translate(-256, -256): (486-256, 175-256) = (230, -81)
Step 2 - scale(0.12): (230×0.12, -81×0.12) = (27.6, -9.72)
Step 3 - translate(25, 50): (25+27.6, 50-9.72) = (52.6, 40.28)
```

```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <g transform="translate(25, 50) scale(0.12) translate(-256, -256)">
    <path d="M79.238 115.768..." fill="#333"/>
  </g>

  <!-- Muzzle flash at calculated (52.6, 40.28) -->
  <g transform="translate(52.6, 40.28)">
    <polygon points="0,0 15,-8 12,0 15,8" fill="#FF6600">
      <animate attributeName="opacity" values="1;0;1" dur="0.1s" repeatCount="indefinite"/>
    </polygon>
  </g>
</svg>
```

### Common Attachment Points

| Icon Type | Attachment Point | How to Find |
|-----------|------------------|-------------|
| Guns/Weapons | Barrel tip | Rightmost X, mid-height Y |
| Swords/Blades | Blade tip | Topmost or rightmost point |
| Characters | Hand position | Look for arm/hand path segments |
| Vehicles | Exhaust/Wheels | Bottom or rear coordinates |

### Debugging
Add a debug circle at calculated position: `<circle cx="52.6" cy="40.28" r="3" fill="red"/>`