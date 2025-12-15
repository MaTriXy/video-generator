---
name: asset-creator
description: Expert SVG asset creator with production-ready output. Searches and integrates icons, creates custom SVG elements, animations, and characters. Outputs clean, self-contained SVG code with transparent backgrounds.
---

# Asset Creator Skill

## CRITICAL: Asset Manifest Priority

**If you receive an `asset_manifest`:**
- **DO NOT create new assets** that already exist in the manifest
- Use the pre-generated assets from the provided paths
- Only create NEW assets that are NOT in the manifest
## Core Responsibility

Create SVG assets using fetched icons and/or custom SVG elements.

- **SVG code only** - No React, no JavaScript, slight animations
- **Transparent background** - No background unless explicitly requested

---
## **References that you will need to create perfect assets**
**Understand Requirements** → Determine what icons/shapes/illustrations/graphics are needed

### **Fetch Icons** → To get references from icons before creating any assets
Read [fetching-icons.md](./references/fetching-icons.md)

### **Learn SVG Basics** → Use whenever SVGs need to be created or used
Read [svg-fundamentals.md](./references/svg-fundamentals.md)

### **Position Elements** → Important to position anything in the scene
Read [viewbox-positioning.md](./references/viewbox-positioning.md)

### **Path Creation** → To create any lines, curves, paths, this is important that you use the learnings from this
Read [path-creation.md](./references/path-creation.md)

### **Animations** → Use whenever any object might need animation
Read [animations.md](./references/animations.md) for details about creating animations.

### **Character Creation** → Whenver scene needs characters, use this
Read [primitive-characters.md](./references/character/primitive-characters.md)

---

## Output Format

Always output a complete, self-contained SVG. Choose viewBox based on use case (see [viewbox-positioning.md](./references/viewbox-positioning.md)):

```svg
<svg viewBox="0 0 [width] [height]" xmlns="http://www.w3.org/2000/svg">
  <!-- SVG elements here -->
</svg>
```