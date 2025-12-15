# React Video Scene Component Format

This document defines the required format for React video scene components.

## Required Structure

### Imports
```typescript
import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
```

### Props Interface
```typescript
interface SceneProps {
  currentTime: number;
}
```

### Export Pattern
```typescript
const Scene{N} = React.memo(function Scene{N}({ currentTime }: SceneProps) {
  // Component implementation
});

export default Scene{N};
```

Where `{N}` is the scene number (e.g., `Scene0`, `Scene1`, `Scene2`)

`currentTime` is the global value of time with respect to the video start.

---

## Sub-Components (CRITICAL)

**All sub-components MUST use `React.memo`** and be defined at module level (outside the main Scene component).

### Why React.memo is Required
- Video components re-render 60 times per second as `currentTime` changes
- Without `React.memo`, sub-components re-render unnecessarily causing animation jitter
- Module-level definitions ensure stable references across renders

### Sub-Component Pattern
```typescript
// CORRECT: Module-level with React.memo
const TreeNode = React.memo(({
  value,
  position,
  isVisible
}: {
  value: string;
  position: { x: number; y: number };
  isVisible: boolean;
}) => (
  <motion.div animate={isVisible ? "visible" : "hidden"}>
    {value}
  </motion.div>
));

// WRONG: Defined inside component (causes jitter)
export default function Scene0({ currentTime }: SceneProps) {
  // ❌ Never define components here
  const TreeNode = ({ value }) => <div>{value}</div>;
}
```

### What Goes at Module Level (Outside Component)
1. **Sub-components** - Always wrapped with `React.memo`
2. **Animation variants** - Objects defining animation states
3. **Static data** - Positions, configurations that don't change

```typescript
// Animation variants at module level
const fadeVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5 } }
};

// Static positions at module level
const nodePositions = {
  node1: { x: 576, y: 540 },
  node2: { x: 1344, y: 540 }
};

// Sub-component at module level with React.memo
const InfoCard = React.memo(({ title, isVisible }: { title: string; isVisible: boolean }) => (
  <motion.div variants={fadeVariants} animate={isVisible ? "visible" : "hidden"}>
    {title}
  </motion.div>
));
```

---

## Complete Example

```typescript
import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

interface SceneProps {
  currentTime: number;
}

// Animation variants at module level
const nodeVariants = {
  hidden: { scale: 0, opacity: 0 },
  visible: { scale: 1, opacity: 1, transition: { duration: 0.4 } }
};

// Static data at module level
const nodePositions = {
  node1: { x: 576, y: 540 },
  node2: { x: 1344, y: 540 }
};

// Sub-component at module level with React.memo
const TreeNode = React.memo(({
  value,
  position,
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
  // Threshold-based state updates (see performance.md)
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