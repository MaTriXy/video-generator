# Component Positioning Reference

Quick reference for positioning elements in video scenes using Tailwind CSS and framer-motion.

**CRITICAL**: Always use pixel values (px) as mentioned for positioning, This ensures precise, predictable positioning across all canvas sizes.

## Table of Contents

- [Positioning Fundamentals](#positioning-fundamentals)
  - [The Universal Pattern](#the-universal-pattern)
  - [Coordinate System](#coordinate-system)
- [Custom Positioning](#custom-positioning)
- [Why Full Centering Matters](#why-full-centering-matters)
- [Z-Index Layering](#z-index-layering)
- [Related Resources](#related-resources)
---

## Positioning Fundamentals

### The Universal Pattern

For ALL positioning in video scenes, use this consistent pattern with **pixel values**:

A motion.div cannot have absolute positioning, it should be wrapped inside an absolute div that is properly positioned as shown.

```tsx
{/* Outer div: handles positioning with Tailwind using PIXELS */}
<div className="absolute top-[108px] left-[192px] -translate-x-1/2 -translate-y-1/2">
  {/* Inner div: content and animations */}
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
  >
    {/* Your content here */}
  </motion.div>
</div>
```

**Key principles:**
- Outer `div`: Uses `absolute` + pixel positioning classes + full centering transforms
- Inner `motion.div`: Handles animations and content
- **Always use BOTH** `-translate-x-1/2` AND `-translate-y-1/2` for consistent centering
- **Always use pixel values** (e.g., `top-[540px]`) NOT percentages

### Coordinate System

- **Origin**: Top-left corner (0, 0)
- **Top**: 0px at top edge → canvas height at bottom edge
- **Left**: 0px at left edge → canvas width at right edge
- Element centers on the specified coordinates

**Canvas Dimensions:**
- Landscape: 1920×1080px
- Portrait: 1080×1920px

---

## Custom Positioning

Position at any pixel value using the same pattern:

```tsx
{/* Landscape example: position at x=1440px, y=270px */}
<div className="absolute top-[270px] left-[1440px] -translate-x-1/2 -translate-y-1/2">
  <motion.div>{/* content */}</motion.div>
</div>
```

## Why Full Centering Matters

Without `-translate-y-1/2`, the element's **top edge** sits at the pixel value, causing overlaps when elements have varying heights. Full centering positions the element's **center** at the pixel coordinate, ensuring safe spacing.

## Z-Index Layering

Layer elements using Tailwind's z-[index] utilities:

```tsx
{/* Background layer */}
<div className="absolute inset-0 z-[0]">...</div>

{/* Content layer - Landscape center: 540px, 960px */}
<div className="absolute top-[540px] left-[960px] -translate-x-1/2 -translate-y-1/2 z-[10]">
  <motion.div>...</motion.div>
</div>

{/* Overlay layer - Landscape: 216px from top, 1536px from left */}
<div className="absolute top-[216px] left-[1536px] -translate-x-1/2 -translate-y-1/2 z-[20]">
  <motion.div>...</motion.div>
</div>
```

**Standard z-index scale:**
- `z-[0]`: Background
- `z-[10]`: Main content
- `z-[20]`: Overlays/floating elements
- `z-[30]`: UI controls
- `z-[40]`: Modals/dialogs
- `z-[50]`: Top layer

## Related Resources
- [performance.md](./references/performance.md) - Optimization guide
