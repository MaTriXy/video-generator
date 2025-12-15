---
name: video-coder
description: Expert React video scene component creator for educational content. Builds production-grade, visually distinctive components using framer-motion animations, pixel-precise positioning, and optimized performance patterns. Follows strict component format with React.memo, threshold-based state updates, and module-level definitions. Outputs self-contained TSX components with proper timing sync, 60fps performance, and comprehensive reference-based implementation.
---

This skill guides creation of distinctive, production-grade React video scene components that avoid generic "AI slop" aesthetics and follow the aesthetics and style given. Implement real working React code with exceptional attention to details, timing, and creative choices.

**IMPORTANT**: All components MUST follow the format defined in [component-format.md](./references/component-format.md).

The user provides video scene requirements: directions, timing information, visual elements, and educational content. They may include context about the purpose, audience, or technical constraints.

**CRITICAL**: Follow the design and execute it with precision. Bold maximalism and refined minimalism both work - the key is precise implementation of the requirements and smooth animations.

**Assets**: The design may reference assets from the `asset_manifest`. For elements with `type: "asset"`:
- The element's `id` matches an asset name in the manifest
- Read the SVG code from the `path` specified in the manifest
- Copy the SVG code directly into your React component
- The asset is already normalized to its `base_orientation` (e.g., "upward", "right")
- Apply the rotation from the design spec directly - it's already calculated relative to base orientation
- Apply styles (position, size, fill, stroke) from the design spec to the SVG element

Then implement working React code following the component format reference that is:
- Production-grade and functional
- Properly structured with required props and timing patterns
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines
Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Follow the color theme as required
- **Motion**: Use framer-motion for all animations in React video components. Focus on high-impact moments: one well-orchestrated scene entry with staggered reveals (using delay) creates more delight than scattered micro-animations. Sync animations with the given timing in the given design.

- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays and etc. But make sure you follow the given color theme. You can be creative artist following the given design.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the given vision/design. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the design/vision well.

---

## Working with Assets

When the design includes elements with `type: "asset"`, you'll receive an `asset_manifest` with entries like:
```json
{
  "name": "hypersonic_missile_main",
  "path": "Outputs/Assets/v20/hypersonic_missile_main.svg"
}
```

**How to use assets in React:**
1. Read the SVG file from the `path` in the manifest
2. Copy the complete SVG code directly into your React component
3. Apply styles (position, size, rotation, fill, stroke) from the design spec to the SVG element
4. The designer has already calculated rotation relative to base orientation - use the rotation value as-is
5. Assets can be styled/colored using fill and stroke attributes if needed for the design

---
**MANDATORY references for creating React components**

## **Tailwind Arbitrary Values** [tailwind-notes.md](./references/tailwind-notes.md)
All components MUST follow the class conventions defined in this reference.

## **Performance Requirements** [performance.md](./references/performance.md)
All components MUST follow the performance patterns defined here, including state management and subcomponent handling.

## **Component Positioning** [component-positioning.md](./references/component-positioning.md)
All components MUST follow these positioning patterns to prevent common layout issues in React video components.

## **Animation Patterns** [animations.md](./references/animations.md)
Contains detailed animation patterns, code examples, and implementation details for specific animation types.

## **Text Creation** [text-creation.md](./references/text-creation.md)
All text elements MUST follow these patterns.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.