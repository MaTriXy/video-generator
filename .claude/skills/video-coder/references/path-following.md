# Path Following Animation Reference

<overview>
When the design spec includes `"type": "follow-path"`, use the `getPathPoint` utility to animate elements along SVG paths.

**Note:** We cannot use `<animateMotion>` because it runs on its own timeline and cannot be controlled by `currentTime` (no scrubbing, pausing, or sync support).

**For creating paths from design specs**, see **[Path Elements Reference](./path-elements.md)**.
</overview>

---

<critical-props>

## CRITICAL: Path Following Utility is Provided as Props

The `getPathPoint` function is **passed as props** from the VideoPlayer component. It is already defined in the VideoPlayer and shared across all scenes.

The utility automatically aligns ANY element with the path direction.

<scene-props-interface>
**Your SceneProps interface must include:**
```typescript
interface SceneProps {
  currentTime: number;
  getPathPoint: (pathD: string, progress: number, elementOrientation: number) => { x: number; y: number; rotation: number };
}
```

**Element orientation uses numeric degrees:**
- 0° = UP
- 90° = RIGHT
- 180° = DOWN
- 270° = LEFT
- Positive = clockwise, Negative = counter-clockwise
</scene-props-interface>

<scene-destructure>
**And your Scene component must destructure them:**
```typescript
const SceneName = React.memo(function SceneName({ currentTime, getPathPoint }: SceneProps) {
  // Your scene code
});
```
</scene-destructure>

</critical-props>

<requirements>

<requirement-use-props>
1. **Use Props**: Access `getPathPoint` from props. DO NOT embed it inline.
</requirement-use-props>

<requirement-progress-clamping>
2. **Progress Clamping**: The utility handles clamping automatically with `Math.min(progress, 1)` to prevent progress from exceeding 1.0.
</requirement-progress-clamping>

<requirement-state-handling>
3. **State Handling**: When element is visible but not moving, determine if it's waiting at the START (before animation begins) or finished at the END (after animation completes). Check the current time against the animation start time.
</requirement-state-handling>

<requirement-sub-components>
4. **Sub-components**: If you create sub-components that need path-following, pass `getPathPoint` to them as props.
</requirement-sub-components>

<requirement-element-orientation>
5. **Determining Element Orientation**: You MUST determine the correct natural orientation of the element:
   - **For SVG assets from manifest**: Use the asset's `base_orientation` value directly
   - **For SVG shapes you create**: Analyze the shape's points/geometry:
     - Arrow `points="0,-15 15,0 0,15"` → Tip at (15,0) = points RIGHT → Use `90`
     - Arrow `points="-8,0 0,-20 8,0"` → Tip at (0,-20) = points UP → Use `0`
     - Arrow `points="0,-8 20,0 0,8"` → Tip at (20,0) = points RIGHT → Use `90`
   - **Rule**: Find where the "front" or "tip" of the element points in its default position (rotation=0)
   - **Coordinate system**: 0° = UP, positive = clockwise, negative = counter-clockwise
</requirement-element-orientation>

</requirements>

<quick-example>

```typescript
// Simple usage - element pointing upward (0°) following a curved path
const pos = getPathPoint("M 100 500 Q 500 100 900 500", 0.5, 0);
// Returns: { x: 540, y: 400, rotation: 90 }
```

</quick-example>

<full-usage-example>

```typescript
const PATH_D = "M 100 500 Q 500 100 900 500";
const ANIMATION_START = 1000;
const ANIMATION_DURATION = 3000;

const states = useMemo(() => ({
  showElement: relTime >= 0,
  isElementMoving: relTime >= ANIMATION_START && relTime < (ANIMATION_START + ANIMATION_DURATION)
}), [Math.floor(relTime / 42)]);

const elementPos = useMemo(() => {
  if (!states.showElement) {
    return { x: 100, y: 500, rotation: 0 };
  }

  // Specify element's natural orientation in degrees (0°=UP, 90°=RIGHT, 180°=DOWN, 270°=LEFT)
  // For assets: use base_orientation from manifest
  // For shapes: determine from geometry
  const ELEMENT_ORIENTATION = 0;  // pointing UP

  if (!states.isElementMoving) {
    if (relTime < ANIMATION_START) {
      // Waiting at START - get rotation from path start
      return getPathPoint(PATH_D, 0, ELEMENT_ORIENTATION);
    } else {
      // Finished at END - get rotation from path end
      return getPathPoint(PATH_D, 1, ELEMENT_ORIENTATION);
    }
  }

  // Animation in progress - calculate current position and rotation
  const progress = Math.min((relTime - ANIMATION_START) / ANIMATION_DURATION, 1);
  return getPathPoint(PATH_D, progress, ELEMENT_ORIENTATION);
}, [relTime, states.isElementMoving, states.showElement]);

// Render
{states.showElement && (
  <div
    style={{
      left: `${elementPos.x}px`,
      top: `${elementPos.y}px`,
      transform: `translate(-50%, -50%) rotate(${elementPos.rotation}deg)`
    }}
  >
    {/* element content */}
  </div>
)}
```

</full-usage-example>

<static-path-aligned>

When design includes `pathPositions`, use `getPathPoint` to position static elements along a path.

<static-example>
**Example:**
```typescript
const PATH_D = "M 680 920 C ...";  // From Python script
const PROGRESS = [0.1, 0.3, 0.5, 0.7, 0.9];  // From design

const positions = useMemo(() =>
  PROGRESS.map(p => getPathPoint(PATH_D, p, 90))  // 90° = pointing RIGHT
, [getPathPoint]);

return (
  <svg>
    <path d={PATH_D} stroke="#FF0000" strokeWidth={4} fill="none" />
    {positions.map((pos, i) => (
      <polygon
        key={i}
        points="0,-8 20,0 0,8"
        fill="#FF0000"
        transform={`translate(${pos.x},${pos.y}) rotate(${pos.rotation})`}
      />
    ))}
  </svg>
);

</static-example>

</static-path-aligned>

<common-mistakes>

<mistake-wrong-orientation>
### ❌ Wrong Element Orientation

**Problem:** Element rotates incorrectly along the path (appears sideways, backwards, or at wrong angles)

**Example:**
```typescript
// Arrow shape points RIGHT (tip at x=20)
<polygon points="0,-8 20,0 0,8" />

// WRONG - Telling system arrow points UP (0°)
const pos = getPathPoint(PATH_D, progress, 0);
// Result: Arrow rotates 90° off from path direction
```

**Solution:** Use the correct degree value matching the shape's actual orientation
```typescript
// CORRECT - Arrow tip is at x=20 (positive X = RIGHT = 90°)
const pos = getPathPoint(PATH_D, progress, 90);
```

<how-to-determine-orientation>
1. Look at your shape's points/vertices
2. Find the "tip" or "front" coordinate
3. Determine which direction it points (0° = UP, positive = clockwise):
   - Tip at negative Y (e.g., 0,-20) = UP → Use `0`
   - Tip at positive X (e.g., 20,0) = RIGHT → Use `90`
   - Tip at positive Y (e.g., 0,20) = DOWN → Use `180`
   - Tip at negative X (e.g., -20,0) = LEFT → Use `270`
</how-to-determine-orientation>
</mistake-wrong-orientation>

<mistake-autorotate>
### ❌ Using autoRotate Incorrectly

**Problem:** Design specifies `"autoRotate": false` with fixed `"rotation"`, but coder uses `getPathPoint` rotation

<when-fixed-rotation>
```typescript
// Design: "autoRotate": false, "rotation": -90
<div style={{
  left: `${pos.x}px`,
  top: `${pos.y}px`,
  transform: `translate(-50%, -50%) rotate(-90deg)`  // Use design's fixed value
}} />
```
</when-fixed-rotation>

<when-path-rotation>
```typescript
// Design: "autoRotate": true (or not specified)
<div style={{
  left: `${pos.x}px`,
  top: `${pos.y}px`,
  transform: `translate(-50%, -50%) rotate(${pos.rotation}deg)`  // Use calculated rotation
}} />
```
</when-path-rotation>
</mistake-autorotate>

</common-mistakes>
