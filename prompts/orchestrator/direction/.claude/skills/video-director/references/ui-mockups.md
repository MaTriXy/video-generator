# Drawing UI

When the voiceover is talking about or the scene takes place within any UI -- a real product, a fictional app, a website, a phone screen, social media posts, dashboards, anything visual that resembles a user interface -- the `videoDescription` must describe it with enough detail that a coder who has NEVER seen the product could build a pixel-accurate mockup from your words alone. The mockup should look like a screenshot of a real product, not a generic illustration.

> **CRITICAL** When you write "Google Ads-style panel", "Stripe-style checkout", "Slack-style sidebar", or ANY "product-style" reference, you are committing to describe a **full real-product mockup** of that product. This means browser chrome, real layout zones, real element details, real content -- exactly as described in Steps 1-4 below. "Google Ads-style" is NOT a decoration hint. It means "describe the actual Google Ads interface in full detail." If you cannot describe the product's real UI in detail, do not reference it by name -- describe an original fictional UI instead.

## Rules

- **Name the real product** it should look like, or the closest equivalent. "A Stripe checkout," "Slack's sidebar," "VS Code with One Dark theme." If it's fictional, say what real product to base it on.
- **Specify every visible element** -- exact text, exact layout.
- **Describe interaction** -- cursor movement, clicks, typing (exact characters), scrolling (what enters/exits view), hover states, transitions after clicks.
- **Include device chrome** -- browser URL bar with realistic URL, macOS traffic light dots. For phones, just name the device.
- **NEVER specify font sizes in pixels** -- describe the visual weight and hierarchy, not the exact pixel size.
- **NEVER specify colors for real product UIs** -- The code agent knows what Amazon, YouTube, Instagram, Slack, VS Code etc. look like and will use the correct brand colors. Just name the product.
- **Specify the UI to highlight** if there is a specific part of UI that should be highlighted.

## How to Describe a Mockup

Follow this structure top-to-bottom when describing any UI. Think of it as painting the screen layer by layer.

### Step 1: Frame and container

Start with what holds the UI. Name the device or window type, its approximate size relative to the canvas, and its position.

- Browser window: "A Chrome browser window in dark mode filling ~85% of the canvas, centered. macOS title bar with red/yellow/green traffic light dots. Tab showing favicon and page title. URL bar showing 'amazon.com/cart'."
- Phone screen: "An iPhone." or "A Samsung phone."
- Desktop app: "A VS Code window filling ~85% of the canvas. macOS title bar with traffic light dots, title 'app.js -- my-project -- Visual Studio Code'."

### Step 2: Top-level layout zones

Describe the major regions of the UI. Work top to bottom, left to right.

- "Amazon header bar (full width): logo on left, search bar center, account links and cart icon on right."
- "Below header: thin sub-nav strip with text links: 'Today's Deals', 'Customer Service', 'Registry', 'Gift Cards', 'Sell'."
- "Main content area splits into: left sidebar (~20% width) for filters, right area (~80%) for product results."

### Step 3: Elements within each zone

For each zone, describe every visible element with:
- **Exact text content** -- what the button/label/link actually says
- **Visual structure** -- shape, borders, rounded corners, shadows, icons
- **Relative position** -- left/right/center within the zone, stacked/side-by-side

**Good:** "Search bar: category dropdown reading 'All' on the left, input field with typed text 'wireless headphones', search button with magnifying glass icon on the right."

### Step 4: Content details

For cards, lists, feeds, or repeated content -- describe 2-3 items with full detail and indicate how many more exist.

- "Product Card 1: `@headphones` product image on the left. Title 'ProSound Elite Wireless Noise Cancelling Headphones - Bluetooth 5.3, 40hr Battery, ANC' as a link. Below: 4.5 stars with '(32,847)' rating count. Bold price '$49.99', strikethrough 'List: $79.99'. 'FREE delivery Wed, Mar 18'. 'Amazon's Choice' badge."
- "Product Card 2: similar layout. `@keyboard` image. Title 'MechType Pro RGB Mechanical Gaming Keyboard'. 4.3 stars, '(18,234)'. Price '$67.00'."
- "Product Card 3 partially visible, cropped at the bottom edge of the browser."

### Step 5: Focus and highlight sync

When the narration talks about specific elements in a mockup, guide the viewer's eye to each element. Choose the focus technique that creates the smoothest flow for the sequence of elements being discussed.

**Choose ONE focus strategy per scene based on how many elements the narration covers:**

**Strategy A: Zoom once, pan between elements, zoom out at end**
Best when the narration discusses 3+ elements in sequence. Zoom into the first element, then pan smoothly to each subsequent element without zooming out between them. Only zoom out at the very end when the narration moves on from the mockup.

Example: "On 'search bar is prominent' -- zoom into the search bar area. On 'Product images are clear' -- pan from the search bar down to the product images (stay zoomed in). On 'Reviews and ratings' -- pan to the star ratings. On 'checkout process is streamlined' -- zoom back out to the full page view."

**Strategy B: Scale up individual elements**
Best when elements are spread far apart and panning would be disorienting. Instead of zooming the whole mockup, scale up the specific element in place -- it grows larger while everything else stays the same or dims slightly.

Example: "On 'the heart icon for liking' -- the heart icon scales up to 2x its size and pulses. On the next beat -- it shrinks back to normal."

**Strategy C: Dim-and-spotlight**
Best when you want to keep the full mockup visible for context. Keep the mockup at normal zoom but dim everything except the focused element, which stays bright or gets a glow/outline.

Example: "On 'sidebar keeps file navigation organized' -- everything except the sidebar dims to 30% opacity, a subtle glow appears around the sidebar. On 'command palette' -- spotlight shifts to the command palette area, sidebar dims back."

**Strategy D: Single zoom for the whole section**
Best when the narration discusses just 1 element. Simple zoom in, highlight, zoom out.

**Highlight effects** (pick what fits the video's tone):
- Glowing outline around the element
- Pulsing scale (element briefly grows and shrinks)
- Brightness boost on the element
- Dimming everything else
- Pointer/cursor moving to the element
- Animated underline or bracket appearing next to the element

**Highlight visibility rules:**
- Highlights must use **high-contrast colors** that stand out against the mockup. Use bright, saturated colors (vivid yellow, cyan, bright green, electric blue) -- not subtle tints.
- When dimming the background, describe the highlight as **bright and bold** so it pops clearly against the dimmed surroundings.

**Panning rules:**
- When panning to a focused element, the element must be **fully visible and centered** in the zoomed viewport -- never cut off at edges.
- The pan must **hold on the element** for the full duration the narration discusses it -- don't pan away while still talking about it.
- Describe the highlight appearing on the element **while the pan holds**, not during the pan motion.

**IMPORTANT: Never do rapid zoom-in/zoom-out/zoom-in/zoom-out on consecutive elements.** This creates a jarring yoyo effect. If discussing multiple elements, use Strategy A (zoom once + pan) or Strategy B (scale individual elements) or Strategy C (dim-and-spotlight).

## What NOT to Do

- **No pixel font sizes** -- never write "12px text", "14px label", "16px heading". Describe hierarchy instead: "bold heading", "body text", "small caption", "label text".
- **No hex colors for real products** -- never write "#131921", "#007185", "#FF9900" for Amazon or any known product. The code agent knows the brand colors. Just name the product and describe the structure.
- **No vague placeholders** -- never write "some buttons", "a few links", "text content", "various items". Name every element.
- **No empty rectangles** -- never describe "a grey box representing a card" or "colored rectangles for charts". Describe the actual content inside.
- **No generic descriptions** -- "a social media app" tells the coder nothing. "Instagram's feed in light mode with stories row, post cards showing `@sunset` photo, heart/comment/share icons, and '1,247 likes'" tells them everything.
- **Every product reference needs full detail** -- whenever you reference a real product (Google Ads, Stripe, Slack, etc.), describe it with full depth. Include browser chrome, real layout zones, real sidebar items, real content. The coder has never seen the product -- your description is all they have.

## Brand Consistency

For real products (Amazon, YouTube, Instagram, Slack, VS Code, etc.), just name the product. The code agent will apply the correct brand colors, typography, and visual language. Do not specify hex values for known brands.

For fictional UIs, establish consistent branding (name, color palette, logo, typography) from the first scene and maintain it across all subsequent scenes featuring that UI.

## Content Must Fill the Mockup

When describing a UI inside a browser window, phone frame, or app window, make sure the described content is enough to visually fill the container. Empty space at the bottom of a mockup looks broken.

- **Describe enough content items** -- if the container is tall, describe enough cards/rows/items to fill it. 2-3 product cards for a browser, 2-3 feed posts for a phone, etc.
- **Describe large visual elements** -- hero images, product photos, and thumbnails should be described as prominent and large, not small web-scale items.
- **If the mockup has a sidebar + main area**, both columns should have enough content to fill the height.

## Smart Cropping for Mobile Readability

**CRITICAL:** Videos are watched on mobile devices where small details become unreadable. Do NOT show full-screen desktop UIs that shrink everything to tiny sizes.

**Instead, intelligently crop and focus:**

1. **Identify the relevant section** -- What part of the UI is the narration actually talking about? The search bar? The checkout button? The notification panel?

2. **Show ONLY that section + immediate context** -- Crop out irrelevant UI chrome. If the narration mentions "YouTube search bar", don't show the entire homepage with video grid. Show a cropped view of the top navigation area with the search bar prominent.

3. **Center and scale for readability** -- The important UI elements should occupy the majority of screen space (70-80%), but not edge-to-edge. Leave breathing room.

4. **Examples of smart cropping:**
   - Narration: "Amazon checkout button" -> Show the checkout section zoomed in, not the entire desktop page
   - Narration: "Instagram story upload" -> Show the phone interface with the story creation UI, not a tiny phone in the middle of a desktop screen
   - Narration: "Slack notification" -> Show the notification panel and relevant message, not the entire Slack workspace
   - Narration: "Gmail compose window" -> Show the compose modal filling most of the screen, not a small window within a full Gmail interface

