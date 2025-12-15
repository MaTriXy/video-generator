# Animation Reference Guide

**IMPORTANT:** Read ALL relevant animation references thoroughly before implementing. Each reference contains complete working code examples with implementation details. Be thorough in studying any animation pattern you're using in your scene.

---

## Transition Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Tween** | Duration-based, precise timing | Coordinated animations, sync with audio |
| **Spring** | Physics-based, bounce/elasticity | Interactive UI, natural motion |
| **Inertia** | Momentum-based deceleration | Drag interactions, swipe gestures |

---

## Tween

```tsx
transition={{
  duration?: number,        // Seconds (default: 0.3)
  ease?: string | array,    // Easing function (default: "easeInOut")
  delay?: number,           // Delay in seconds
  repeat?: number,          // Number of repeats (Infinity for loop)
  repeatType?: "loop" | "reverse" | "mirror",
  times?: number[],         // Keyframe timing [0, 0.5, 1]
}}
```

### Easing Functions

| Ease | Behavior | Use Case |
|------|----------|----------|
| `linear` | Constant speed | Mechanical motion, loading indicators |
| `easeIn` | Slow → fast | Exit animations, falling objects |
| `easeOut` | Fast → slow | Entrances, coming to rest |
| `easeInOut` | Slow → fast → slow | Default for most UI animations |
| `circIn/Out/InOut` | Sharper circular curve | Snappy, aggressive motion |
| `backIn` | Pulls back, then forward | Anticipation effects |
| `backOut` | Overshoots, then settles | Bouncy clicks, attention-grabbing |
| `backInOut` | Both effects combined | Playful, game UI |
| `anticipate` | Dramatic pullback | Hero entrances, launch effects |
| `steps(n)` | Discrete steps | Pixel art, frame-by-frame |

**Example:**
```tsx
<motion.circle
  animate={{ cy: 200 }}
  transition={{ duration: 1.5, ease: "easeOut" }}
/>
```

---

## Spring

Only supports 2 keyframes (from → to).

**Option 1: Physics-based**
```tsx
transition={{
  type: "spring",
  stiffness?: number,  // Tightness (1-100: soft, 150-300: standard, 400-600: snappy)
  damping?: number,    // Resistance (higher = less bounce, 0 = infinite oscillation)
  mass?: number,       // Weight (higher = more lethargic)
}}
```

**Option 2: Duration-based**
```tsx
transition={{
  type: "spring",
  bounce?: number,     // 0-1 bounciness
  duration?: number,   // Seconds
}}
```

**Note:** Cannot mix `bounce` with `stiffness`/`damping`/`mass`.

**Examples:**
```tsx
// Bouncy
transition={{ type: "spring", bounce: 0.6 }}

// Snappy
transition={{ type: "spring", stiffness: 400, damping: 30 }}

// Soft
transition={{ type: "spring", stiffness: 60, damping: 10 }}
```

---

## Inertia

For drag interactions:

```tsx
<motion.div
  drag
  dragConstraints={{ left: 0, right: 400 }}
  dragTransition={{
    power?: number,           // Deceleration rate (default: 0.8)
    timeConstant?: number,    // Duration in ms (default: 700)
    bounceStiffness?: number, // Boundary spring (default: 500)
    bounceDamping?: number,   // Boundary damping (default: 10)
  }}
/>
```

---

## Rotation

```tsx
// Clockwise rotation (positive degrees)
<motion.div animate={{ rotate: 90 }} transition={{ duration: 1 }} />

// Anti-clockwise rotation (negative degrees)
<motion.div animate={{ rotate: -90 }} transition={{ duration: 1 }} />

// Continuous clockwise spin
<motion.div
  animate={{ rotate: 360 }}
  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
/>

// Continuous anti-clockwise spin
<motion.div
  animate={{ rotate: -360 }}
  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
/>

// Custom pivot point
<motion.div
  style={{ transformOrigin: "top left" }}
  animate={{ rotate: 45 }}
/>
```

**Properties:**
- `rotate` - 2D rotation in degrees (positive = clockwise, negative = anti-clockwise)
- `rotateX`, `rotateY` - 2D axis rotation
- `transformOrigin` - pivot point (default: `"center"`)

---

## Property-Specific Transitions

```tsx
transition={{
  x: { type: "spring", stiffness: 200 },
  opacity: { duration: 0.5, ease: "easeOut" },
  scale: { type: "spring", bounce: 0.6 }
}}
```
