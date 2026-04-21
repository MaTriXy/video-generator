---
name: fonts
description: Loading Google Fonts and local fonts in Remotion, measuring text, and responsive font sizing
metadata:
  tags: fonts, google-fonts, typography, text, measuring-text
---

<remotion-font>
# Using fonts in Remotion

## Google Fonts with @remotion/google-fonts

The recommended way to use Google Fonts. It's type-safe and automatically blocks rendering until the font is ready.

```tsx
import { loadFont } from "@remotion/google-fonts/Lobster";

const { fontFamily } = loadFont();

export const MyComposition = () => {
  return <div style={{ fontFamily }}>Hello World</div>;
};
```

Preferrably, specify only needed weights and subsets to reduce file size:

```tsx
import { loadFont } from "@remotion/google-fonts/Roboto";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});
```

### Waiting for font to load

Use `waitUntilDone()` if you need to know when the font is ready:

```tsx
import { loadFont } from "@remotion/google-fonts/Lobster";

const { fontFamily, waitUntilDone } = loadFont();

await waitUntilDone();
```

## Local fonts with @remotion/fonts

For local font files, use the `@remotion/fonts` package.

### Loading a local font

Place your font file in the `public/` folder and use `loadFont()`:

```tsx
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

await loadFont({
  family: "MyFont",
  url: staticFile("MyFont-Regular.woff2"),
});

export const MyComposition = () => {
  return <div style={{ fontFamily: "MyFont" }}>Hello World</div>;
};
```

### Loading multiple weights

Load each weight separately with the same family name:

```tsx
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

await Promise.all([
  loadFont({
    family: "Inter",
    url: staticFile("Inter-Regular.woff2"),
    weight: "400",
  }),
  loadFont({
    family: "Inter",
    url: staticFile("Inter-Bold.woff2"),
    weight: "700",
  }),
]);
```

### Available options

```tsx
loadFont({
  family: "MyFont", // Required: name to use in CSS
  url: staticFile("font.woff2"), // Required: font file URL
  format: "woff2", // Optional: auto-detected from extension
  weight: "400", // Optional: font weight
  style: "normal", // Optional: normal or italic
  display: "block", // Optional: font-display behavior
});
```

## Using in components

Call `loadFont()` at the top level (module scope) and pass the `fontFamily` via the `Text` component's `textStyles` prop. Never set `fontSize` directly — the `Text` component auto-sizes based on `width` (px) and `height` (px).

```tsx
import { loadFont } from "@remotion/google-fonts/Montserrat";

const { fontFamily } = loadFont("normal", {
  weights: ["400", "700"],
  subsets: ["latin"],
});

// Inside your scene component, use the Text prop:
<Text text="Hello World" width={600} height={100} textStyles={{ fontFamily, fontWeight: 700 }} />
```
</remotion-font>

<remotion-measuring-text>

# Text sizing in Remotion

**Do NOT use `measureText()`, `fitText()`, or `fillTextBox()` from `@remotion/layout-utils` for text sizing.** The `Text` component (received as a prop) handles all text measurement and auto-sizing automatically.

Simply use the `Text` component with appropriate `width` (px) and `height` (px) — the font size is calculated to fit the container.

```tsx
// Font loading at module level
import { loadFont } from "@remotion/google-fonts/Inter";
const { fontFamily } = loadFont("normal", { weights: ["400", "700"], subsets: ["latin"] });

// Inside scene component — use Text prop for all text rendering
<Text text="Hello World" width={500} height={80} textStyles={{ fontFamily, fontWeight: 700 }} />
```
</remotion-measuring-text>

<text-decorations>

# Decorating specific words (underlines, highlights, circles, etc.)

Since the `Text` component auto-sizes the font, you CANNOT reliably position decorations (SVG underlines, highlight boxes, circles) by guessing pixel offsets on a single `Text` component. Instead, split the sentence into multiple `Text` components arranged in a flex row — one for normal words and one for the decorated words. Place the decoration (e.g. SVG underline) as a child of the decorated word's wrapper div, where the bounds are known exactly.

This applies to ANY visual decoration targeting specific words: underlines, circles, boxes, highlights, strikethroughs, etc. Always split the text so the decoration's container matches the target word's container.
</text-decorations>
