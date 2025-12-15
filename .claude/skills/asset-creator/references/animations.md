# Animation Reference Guide

**IMPORTANT:** Read ALL relevant animation references thoroughly before implementing. Each reference contains complete working code examples with implementation details. Be thorough in studying any animation pattern you're using in your SVG asset.

This master document provides an overview of all animation patterns available for SVG assets.

## Animation Categories

### Rotation Animations
- **[rotation-animations.md](./references/animations/rotation-animations.md) - READ THIS FOR ANY OBJECT THAT ROTATES** - Works for ANY rotating element (wheels, gears, doors, levers, etc.). Contains guidelines and links to example files covering every type of rotation pattern from simple pivots to complex systems with attached objects.

### Path Following Animations
- **[path-following.md](./references/animations/path-following.md) - READ THIS FOR ANY OBJECT FOLLOWING A PATH** - Explains how to make and object follow any path. Works with `<animateMotion>` + `<mpath>` for any SVG element.

### Path Drawing Animations
- **[path-drawing.md](./references/animations/path-drawing.md) - READ THIS FOR DRAWING/REVEALING PATHS** - Animates the drawing of a path itself (line appearing on screen). Uses `stroke-dasharray` and `stroke-dashoffset` technique.

