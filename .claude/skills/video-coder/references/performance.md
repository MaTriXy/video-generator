# Performance Optimization for React Video Components

**CRITICAL**: Follow these patterns to prevent animation jittering and re-rendering issues.

## Core Problem

React video components re-render up to 60 times per second. Unstable references cause animations to restart, creating visual jitter.

---

## Required Patterns

### 1. Module-Level Definitions

Define sub-components, animation variants, and static data **outside** the parent component for stable references.

```tsx
// Animation variants
const nodeVariants = {
  hidden: { scale: 0, opacity: 0 },
  visible: { scale: 1, opacity: 1, transition: { duration: 0.4 } }
};

// Static data (positions in pixels, styles)
const nodePositions = {
  node1: { x: 576, y: 540 },   
  node2: { x: 740, y: 540 }, 
};

// Sub-component with React.memo
const TreeNode = React.memo(({
  value,
  position,  // Position in pixels
  isVisible
}: {
  value: string;
  position: { x: number; y: number };
  isVisible: boolean;
}) => (
  <motion.div
    variants={nodeVariants}
    initial="hidden"
    animate={isVisible ? "visible" : "hidden"}
  >
    {value}
  </motion.div>
));
```

### 2. Threshold-Based State Updates always inside the component

Update states every 250ms using `Math.floor(currentTime / 250)` to prevent excessive re-renders.

```tsx
// State updates inside components
const states = useMemo(() => ({
  showTitle: currentTime >= 1000,
  showGrid: currentTime >= 2000,
  fadeOut: currentTime >= 9000
}), [Math.floor(currentTime / 250)]);

// Computed collections inside components
const visibleItems = useMemo(() => {
  const visible = new Set<string>();
  if (currentTime >= 1000) visible.add('item1');
  if (currentTime >= 2000) visible.add('item2');
  return visible;
}, [Math.floor(currentTime / 250)]);

// Static data created once at mount
const particles = useMemo(() =>
  Array.from({ length: 40 }, () => ({
    x: Math.random() * 100,
    y: Math.random() * 100
  })),
  [] // Empty deps = created once
);
```

**Threshold Guidelines:**
- `250ms` (4 updates/sec): Default for most animations
- `500ms` (2 updates/sec): Slow transitions

### 3. Explicit Props for Memoization

Pass all dependencies as explicit props for `React.memo` to work correctly.

```tsx
const TreeNode = React.memo(({
  value,
  showTree  // Explicit prop, not derived from currentTime inside
}: {
  value: string;
  showTree: boolean;
}) => (
  <motion.div animate={showTree ? "visible" : "hidden"} />
));

// In parent: derive state, pass as prop
<TreeNode value="50" showTree={states.showTree} />
```

---

## Complete Example

```tsx
import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

interface SceneProps {
  currentTime: number;
}

const nodeVariants = {
  hidden: { scale: 0, opacity: 0 },
  visible: { scale: 1, opacity: 1, transition: { duration: 0.4 } }
};

const nodePositions = {
  node1: { x: 576, y: 540 },   
  node2: { x: 1344, y: 540 }, 
};

const TreeNode = React.memo(({
  value,
  position,  // Position in pixels
  isVisible
}: {
  value: string;
  position: { x: number; y: number };
  isVisible: boolean;
}) => (
  <div
    className="absolute -translate-x-1/2 -translate-y-1/2"
    style={{ left: `${position.x}px`, top: `${position.y}px` }}
  >
    <motion.div
      variants={nodeVariants}
      initial="hidden"
      animate={isVisible ? "visible" : "hidden"}
      className="w-20 h-20 rounded-full bg-white flex items-center justify-center"
    >
      {value}
    </motion.div>
  </div>
));

// Main Scene component with React.memo
const Scene0 = React.memo(function Scene0({ currentTime }: SceneProps) {
  const states = useMemo(() => ({
    showNode1: currentTime >= 1000,
    showNode2: currentTime >= 2000,
  }), [Math.floor(currentTime / 250)]);

  return (
    <div className="relative w-full h-full bg-gray-900">
      <TreeNode value="A" position={nodePositions.node1} isVisible={states.showNode1} />
      <TreeNode value="B" position={nodePositions.node2} isVisible={states.showNode2} />
    </div>
  );
});

export default Scene0;
```

**Summary**
Always use useMemo inside React components to prevent animation jitter caused by 60fps re-renders—define static data and sub-components at module level, use threshold-based state updates (250ms intervals), and pass explicit props for memoization.