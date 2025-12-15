# Text Creation Guidelines
**IMPORTANT:** 
- All text elements MUST be wrapped in a container div with `w-fit h-fit` and padding. The container div also handles positioning using classes from [component-positioning.md](./references/component-positioning.md).
- Always use z-index values to control layering.
- Do not set fontFamily to the text let it use the default font-family set in the parent
---

## Container Pattern (REQUIRED)

```tsx
{/* Container: positioning + fit dimensions + padding */}
<div className="absolute -translate-x-1/2 -translate-y-1/2 top-[100px] left-[50px] w-fit h-fit p-[24px] z-[5]">
  <motion.span className="relative z-[6] ...">Your Text</motion.span>
</div>
```

**Key requirements:**
- `w-fit h-fit` - Container fits content exactly
- `p-[Npx]` - Padding must use pixel values in brackets (e.g., `p-[24px]`, `p-[16px]`)
---

## Filled Background Reveal

```tsx
<div className="absolute -translate-x-1/2 -translate-y-1/2 top-[80px] left-[60px] w-fit h-fit p-[24px] z-[5]">
  <motion.div className="relative inline-block z-[6]">
    <motion.div
      className="absolute inset-0 bg-amber-500 z-[0]"
      initial={{ scaleX: 0 }}
      animate={{ scaleX: 1 }}
      style={{ transformOrigin: "left" }}
      transition={{ duration: 0.8, ease: "easeOut" }}
    />
    <motion.span
      className="relative z-[10] px-[16px] py-[8px] text-[48px] font-bold text-white block"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.4 }}
    >
      Revealed Text
    </motion.span>
  </motion.div>
</div>
```

---

## Frosted Glass

```tsx
<div className="absolute -translate-x-1/2 -translate-y-1/2 top-[150px] left-[80px] w-fit h-fit p-[24px] z-[5]">
  <motion.div
    className="inline-block bg-white/10 backdrop-blur-lg border border-white/20 rounded-2xl z-[6]"
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
  >
    <span className="block px-[32px] py-[20px] text-[40px] text-white/90 z-[7]">Frosted</span>
  </motion.div>
</div>
```

---

## Letter-by-Letter Reveal

```tsx
<div className="absolute -translate-x-1/2 -translate-y-1/2 top-[100px] left-[80px] w-fit h-fit p-[24px] flex z-[5]">
  {"TEXT".split("").map((char, i) => (
    <motion.span
      key={i}
      className="text-[52px] font-black text-emerald-400 px-[4px] z-[8]"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.08, duration: 0.4 }}
    >
      {char}
    </motion.span>
  ))}
</div>
```

---

## Highlight Marker

```tsx
<div className="absolute -translate-x-1/2 -translate-y-1/2 top-[100px] left-[80px] w-fit h-fit p-[24px] z-[5]">
  <div className="relative inline-block z-[6]">
    <motion.div
      className="absolute inset-0 bg-yellow-300/70 -rotate-1 rounded-sm z-[0]"
      initial={{ scaleX: 0 }}
      animate={{ scaleX: 1 }}
      style={{ transformOrigin: "left" }}
    />
    <span className="relative z-[10] px-[12px] py-[4px] text-[38px] font-bold text-gray-900">Highlighted</span>
  </div>
</div>
```

---

## Gradient Text

```tsx
<div className="absolute -translate-x-1/2 -translate-y-1/2 top-[100px] left-[60px] w-fit h-fit p-[24px] z-[5]">
  <motion.span
    className="block px-[16px] py-[8px] text-[52px] font-black bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 bg-clip-text text-transparent z-[9]"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
  >
    Gradient Text
  </motion.span>
</div>
```

---

## Text Outline

```tsx
<div className="absolute -translate-x-1/2 -translate-y-1/2 top-[120px] left-[80px] w-fit h-fit p-[24px] z-[5]">
  <motion.span
    className="block text-[56px] font-black z-[8]"
    style={{ color: "transparent", WebkitTextStroke: "2px #fff" }}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
  >
    OUTLINE
  </motion.span>
</div>
```

---

## Padding Reference

| Text Size | Padding |
|-----------|---------|
| 16-24px | `p-[8px]` to `p-[12px]` |
| 28-36px | `p-[16px]` to `p-[20px]` |
| 40-52px | `p-[24px]` to `p-[32px]` |
| 56px+ | `p-[32px]` to `p-[48px]` |

---

## Rules

1. Always wrap text in a positioned container div with `w-fit h-fit` and padding
2. Padding must use pixel values: `p-[Npx]` (e.g., `p-[24px]`, `px-[16px]`, `py-[8px]`)
3. Use `inline-block` for backgrounds that fit text content
4. Use `block` on inner spans for proper padding
5. Use `overflow-hidden` when animating backgrounds
6. Set `relative z-[10]` on text layers over animated backgrounds
