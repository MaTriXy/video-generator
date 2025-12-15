# Text Guidelines

## Core Rules

### 1. Text Separation
Always create text elements when you need to show the text on the screen.

### 2. Auto-sizing

Text elements are auto-sized based on content and fontSize.

---

## Text Schema 

**Schema:** Read this to understand the text schema. [text-schema.md](./text/text-schema.md)

---

## Text Container & Backgrounds

**IMPORTANT: Never create separate shape elements for text backgrounds. Use the `container` object instead.**

The `container` object gives text its own background, border, and padding. The background automatically sizes to fit the text content.

### Background Types Guide

#### 1. **solid** - Simple colored background
**Use for:**
- Clear, readable labels
- Emphasis and highlighting
- Simple badges or tags
- Maximum readability

#### 2. **gradient** - Multi-color blend
**Use for:**
- Eye-catching titles
- Modern, vibrant designs
- Brand-focused elements
- Creative emphasis

#### 3. **frosted-glass** - Blurred transparency
**Use for:**
- Modern, elegant overlays
- Text over complex backgrounds
- Depth and layering effects
- Professional, polished look

**Requires `backdropBlur` field:**

#### 4. **highlight** - Marker/underline effect
**Use for:**
- Emphasizing specific words
- Casual, hand-drawn feel
- Educational content
- Drawing attention

#### 5. **none** - No background
**Use for:**
- Clean, minimal text
- When padding is needed but no background
- Text over simple backgrounds

### Padding Guidelines

Padding creates space between text and container edges. Choose based on text size:

| Text Size | Recommended Padding |
|-----------|-------------------|
| 16-24px | 8-12px |
| 28-36px | 16-20px |
| 40-52px | 24-32px |
| 56px+ | 32-48px |

**Padding Tips:**
- Larger text → larger padding for proportion
- Tight designs: use minimum padding
- Spacious designs: use maximum padding
- Square/pill shapes: adjust padding to control shape

### Border Guidelines

Borders add definition and style to text containers.

**Border radius:**
- `0` - Sharp corners (technical, formal)
- `4-8` - Subtle rounds (modern, clean)
- `12-16` - Rounded (friendly, approachable)
- `999` - Pill shape (badges, tags)

**Border width:**
- `1-2px` - Subtle outline
- `3-4px` - Bold definition
- `5+px` - Strong emphasis

**Border colors:**
- Match text color for cohesion
- Contrast for separation
- White/black for universal compatibility

### Backdrop Blur Guidelines

Only used with `frosted-glass` background type.

- `sm` - Subtle blur (8px) - text remains clear
- `md` - Medium blur (12px) - balanced effect
- `lg` - Strong blur (16px) - prominent glassmorphism
- `xl` - Maximum blur (24px) - heavy frosted effect

## Typography Best Practices

### Font Size Guidelines
- **Headings:** 48-72px
- **Subheadings:** 36-48px
- **Body text:** 24-36px
- **Captions:** 18-24px 

### Readability Rules
- Use high contrast (dark text on light background or vice versa)
- Place text over solid backgrounds or use backdrops for busy backgrounds
- Keep text within viewport boundaries

### Line Height Guidelines
- Short text (1-2 lines): `1.0-1.2`
- Paragraph text (3+ lines): `1.4-1.6`
- Tight spacing: `1.0` (for impact)
- Comfortable reading: `1.5`

### Font Weight Guidelines
- Light: 300 (subtle, elegant)
- Normal: 400 (default body text)
- Semi-bold: 600 (emphasis)
- Bold: 700 (headings, strong emphasis)
- Extra bold: 800-900 (maximum impact)

---

## Text Alignment

Use appropriate alignment for content type:
- `center`: For titles and centered layouts
- `left`: For paragraphs and multi-line content
- `right`: For design balance (use sparingly)
