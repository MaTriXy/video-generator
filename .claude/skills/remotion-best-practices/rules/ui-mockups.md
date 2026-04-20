---
name: ui-mockups
description: Mandatory rules for building UI mockups (websites, apps, dashboards, browser windows, phone screens) in video scenes. Covers text sizing, content fill, realism, and layout.
metadata:
  tags: mockup, ui, website, app, dashboard, card, layout, readability, browser, phone
---

# UI Mockups in Video Scenes — Mandatory Rules

## 0. These Rules Override the Artstyle — No Exceptions

When building a UI mockup, this file is the **sole authority** on visual styling. The `<artstyle>` block defines the video canvas around the mockup -- it does NOT apply inside the mockup.

Make the mockup look like the actual product. Not the video's art style.

### UI Font Families — Use These Inside Mockups, NOT Artstyle Fonts

The `<artstyle>` block includes fonts for the video canvas. **Inside UI mockups, use the fonts below instead.** These are purpose-built for realistic UI rendering. The artstyle also has its own fonts — those are for the video canvas only, NOT for UI mockups.

```json
{
  "font_families": [
    {
      "usecase": "Body text, labels, buttons, inputs, navigation, and general interface elements",
      "fonts": [
        {
          "name": "Jost",
          "weights": ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
          "subsets": ["cyrillic", "latin", "latin-ext"]
        }
      ]
    },
    {
      "usecase": "Headings, hero text, and display-size typographic moments at large sizes",
      "fonts": [
        {
          "name": "Jost",
          "weights": ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
          "subsets": ["cyrillic", "latin", "latin-ext"]
        },
        {
          "name": "PlayfairDisplay",
          "weights": ["400", "500", "600", "700", "800", "900"],
          "subsets": ["cyrillic", "latin", "latin-ext", "vietnamese"]
        }
      ]
    },
    {
      "usecase": "Code blocks, terminal output, inline code snippets, and developer-facing content",
      "fonts": [
        {
          "name": "IBMPlexMono",
          "weights": ["100", "200", "300", "400", "500", "600", "700"],
          "subsets": ["cyrillic", "cyrillic-ext", "latin", "latin-ext", "vietnamese"]
        }
      ]
    },
    {
      "usecase": "Numeric displays, data tables, timestamps, counters, and fixed-width aligned content",
      "fonts": [
        {
          "name": "IBMPlexMono",
          "weights": ["100", "200", "300", "400", "500", "600", "700"],
          "subsets": ["cyrillic", "cyrillic-ext", "latin", "latin-ext", "vietnamese"]
        }
      ]
    },
    {
      "usecase": "Long-form reading, articles, blog posts, documentation, and editorial body text",
      "fonts": [
        {
          "name": "IBMPlexSerif",
          "weights": ["100", "200", "300", "400", "500", "600", "700"],
          "subsets": ["cyrillic", "cyrillic-ext", "latin", "latin-ext", "vietnamese"]
        }
      ]
    },
    {
      "usecase": "Formal documents, letters, reports, legal text, and professional communications",
      "fonts": [
        {
          "name": "IBMPlexSerif",
          "weights": ["100", "200", "300", "400", "500", "600", "700"],
          "subsets": ["cyrillic", "cyrillic-ext", "latin", "latin-ext", "vietnamese"]
        }
      ]
    }
  ]
}
```

**Rules:**
- For real product mockups (Google, Slack, VS Code, etc.), use the actual product's font if you know it. Fall back to these UI fonts if unsure.
- For fictional/generic UI mockups, always use these fonts — never the artstyle fonts.
- Load all fonts via `@remotion/google-fonts`.

---

When the direction describes a UI -- a real product, website, app, phone screen, dashboard, browser window, or any interface -- your job is to make it look like the **real product**. The direction tells you WHAT to show; you decide HOW to size and color it for video.

## 1. Text Sizing — Override Direction Pixel Sizes

The direction may describe text with web-scale pixel sizes (9px, 12px, 14px, 16px) -- **ignore those sizes**. They are web-accurate but unreadable in video.

**Use the `Text` component (received as a prop) for ALL text inside mockups** -- nav items, button labels, sidebar links, card metadata, input placeholders, status bars, divider text, "Powered by" labels, everything. **NEVER use raw `<span>` with hardcoded `fontSize` for text inside mockups.** The ONLY exception is syntax-highlighted code spans (which need raw `<span>` with explicit fontSize 28-38px). Any `<span style={{ fontSize: ... }}>` for a label, button, or any readable text inside a mockup is wrong — always use `<Text>` instead.

**Minimum Text component heights inside mockups:**
- Headings / titles: `height` >= 100px
- Body text / labels / nav items: `height` >= 65px
- Smallest captions / metadata: `height` >= 50px
- Never pass `height` < 50px to `Text` inside a mockup

**Portrait (1080x1920) mockups -- CRITICAL:**
- Do NOT shrink a desktop mockup to fit portrait. Redesign the layout vertically.
- Browser/phone mockups must span >= 90% of the 1080px width (972px+).
- Prefer showing fewer elements at readable sizes over cramming everything in small.
- Stack elements vertically instead of placing them side by side.

## 2. Content Must Fill the Container (But Stay Centered on Canvas)

Mockup content must fill the available height inside its container (browser window, phone frame, app window). Empty space at the bottom of a mockup looks broken.

**IMPORTANT: The mockup container itself must still be centered on the canvas.** "Fill the container" means make elements larger within the mockup — NOT start the mockup from the top of the canvas. The mockup as a whole must be vertically and horizontally centered, then content fills the mockup's internal space.

**How to fill the height:**
- **Scale up images and cards** -- product images, thumbnails, food photos, hero images should be sized to fill the container. If a browser has ~700px of content space and 3 product cards, each card should be ~220px+ tall with large images, not 140px web-scale images.
- **Scale up spacing** -- padding, margins, and gaps between elements should be 2-3x web scale. Card padding: 16-24px. Gaps between cards: 20-30px. Section margins: generous.
- **Scale up interactive elements** -- search bars: 50px+ tall. Buttons: 44px+ tall. Pills/chips: 40px+ tall. These are video elements, not web elements.
- **After laying out all content, check for empty space** inside the mockup. If there is any, increase element sizes until the content fills the mockup's internal space.

## 3. Brand Colors — Use Real Product Colors

For real products (Amazon, YouTube, Instagram, Slack, VS Code, etc.), use the actual brand colors even if the direction doesn't specify them. You know what these products look like -- apply the correct color palette, not generic colors.

When a mockup represents a real product, the mockup must look like that product — not like the video's art style. Render the mockups the way it actually looks, regardless of the video art style. The art style controls the videos canvas around the mockup, not the mockup itself.

For fictional UIs, follow any color guidance from the direction.

## 4. Realistic Structure

A realistic mockup has:
- **Real UI structure** -- actual nav bars with real items, actual sidebars with real links, actual cards with real content.
- **Real text labels** -- actual button text ("Sign In", "Subscribe", "Add to Cart"), actual menu items, actual placeholder text.
- **Every element must look like it belongs in a real product** -- buttons with proper styling, icons that are recognizable, cards with proper shadows and structure.

## 5. Proportions (Scaled for Video)

Everything in a mockup must be scaled up from real-world web/app proportions:
- **Borders** -- 3-4px minimum. A 1px border is invisible in video.
- **Rounded corners** -- at least `borderRadius: 12px` for containers, `8px` for smaller elements.
- **Icons/thumbnails** -- minimum 50x50px.
- **Contrast** -- increase contrast without breaking the brand theme. Video needs stronger contrast than web.

## 6. Code Editor / Terminal Mockups

Code uses syntax-highlighted spans (multiple colors per line), so the `Text` component can't be used for code lines. When rendering code with raw `<span>` elements:

- **`fontSize: 28px` to `38px`** for code text. Never go below 28px.
- **Line numbers** -- `fontSize: 22px` to `26px`.
- **Show fewer lines, larger** -- 6-8 lines max. Only show what the narration references.
- **Line height** -- `lineHeight: 1.6` for breathing room.
- **Editor chrome matters** -- title bar (traffic light dots or tab bar), line numbers column, syntax theme colors.

## 7. Browser Window Mockups

- **Always include browser chrome** -- tab bar with favicon and page title, URL bar with a realistic URL, navigation buttons.
- Use the correct browser theme (dark/light).
- Page content inside must follow rules 1-5 above.

## 8. Phone Screen Mockups

- **Shape of phone** -- Draw realisitic phone and draw micro-details inside it so it looks real
- App content must look like the actual app -- real tab bars, real navigation patterns, real content cards.
- Content inside the phone must fill the phone screen height -- no empty space at the bottom.

## 9. Dashboard Mockups

- **Charts must have real data** -- labeled axes, data points, legends.
- **Metrics must show real numbers** -- "$12,847", "2,341 users", "+14.2%".
- **Sidebar navigation must have real labels** -- "Overview", "Analytics", "Settings".

**Dashboard content must fill the container height.** After laying out header, charts, tables, and metrics, calculate total content height. If content occupies less than 85% of the container's internal height, you MUST either:
- **Scale up charts, table rows, and spacing** until content fills the container, OR
- **Reduce the container height** to wrap the content (with ~40px bottom padding).

A dashboard with 300px of empty white space at the bottom looks broken. Charts should be taller, table rows should have more vertical padding, and gaps between sections should be generous — fill the space.

**Content area vertical layout:** The content area below the header/nav bar must use `display: "flex", flexDirection: "column", justifyContent: "center"` (or `space-between` / `space-evenly` depending on the layout) so content is vertically centered within the available space — not top-aligned with empty space pooling at the bottom. Top-aligned content with a big empty gap at the bottom looks like a broken web page, not a polished dashboard.

## 10. Animation

- Bring the mockup in as a whole first (slide/scale), then progressively reveal inner content.
- For scroll animations, content should flow naturally with items entering/exiting the viewport.

## 11. Focus and Highlight on Mockup Elements

Implement the focus strategy and highlight effects the direction describes. The direction chooses WHICH strategy (A/B/C/D); you implement HOW.

- **Strategy A (Zoom + pan)**: Use `transform: scale()` on the mockup container with animated `transformOrigin` to pan between elements. Zoom in once, pan to each element, zoom out at the end. Make sure zoomed content stays within canvas bounds.
- **Strategy B (Scale individual elements)**: Scale up the specific element in place using `transform: scale()` on that element only, while dimming others.
- **Strategy C (Dim-and-spotlight)**: Dim non-focused elements to 0.2-0.3 opacity, keep focused element at full opacity with brightness boost and glow.
- **Strategy D (Single zoom)**: Simple zoom in with `transformOrigin` on the element, hold, zoom out.

### Highlight effects — must be highly visible

Highlights must **pop** against the mockup. Use bright, high-contrast, saturated colors.

- **Glowing outline**: double boxShadow (inner tight + outer wide), opacity >= 0.8 on inner glow, minimum spread 20px. Example: `boxShadow: '0 0 24px rgba(0,255,200,0.9), 0 0 48px rgba(0,255,200,0.4)'`
- **Pulsing scale**: element scales 1.08-1.15x and back using spring.
- **Dim others**: reduce opacity of non-focused elements to **0.2-0.3** (not 0.5 — too subtle). The contrast between dimmed and focused must be stark.
- **Brightness boost**: `filter: brightness(1.4)` minimum on the focused element.
- **Animated underline/bracket**: stroke width >= 3px, bright saturated color.

### Panning — fast, intentional, element fully visible

- **Pan duration**: 8-12 frames (0.25-0.4s at 30fps). Use `Easing.out(Easing.quad)` for a fast start that settles quickly.
- **Element must be fully visible and centered** in the zoomed viewport after the pan — never cut off at edges. Clamp `transformOrigin` so the zoomed viewport doesn't extend past canvas bounds.
- **Hold on the element** for the full duration the narration discusses it — don't pan away while still talking about it.
- **Apply the highlight after the pan settles** — add 2-3 frames delay after pan completes before the highlight animates in.

### Timing

- All focus/highlight animations must be synced to the audio transcript frame markers.
- **Never do rapid zoom-in/zoom-out/zoom-in/zoom-out** on consecutive elements. If the direction describes multiple elements in sequence, use Strategy A or B or C — not repeated Strategy D.
