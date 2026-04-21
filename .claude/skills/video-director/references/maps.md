# Maps and Geography

When the voiceover mentions countries, states, regions, continents, locations, travel routes, global distribution, or any geographic concept, the `videoDescription` must describe the map scene with enough detail that it can be rendered accurately using Mapbox.

Real interactive maps are rendered directly using Mapbox GL JS -- you never need to describe "drawing" a map shape. Instead, describe WHAT the map shows and HOW it behaves.

## Rules

- **Never request map assets.** Maps are rendered directly using Mapbox -- never add maps or world-maps to `required_assets`.
- **Name specific locations** -- countries by name, states/provinces by name, cities by name. Do not say "a few countries" -- say which ones.
- **Describe the map's viewport** -- what region is visible (the whole world, a continent, a single country zoomed in), the approximate camera angle (top-down, slightly tilted), and whether the map pans or zooms during the scene.
- **Describe highlights and fills** -- which regions should be highlighted, what visual treatment they get (filled with color, outlined, pulsing, glowing). If different regions get different colors, describe the grouping logic.
- **Describe markers and labels** -- if specific cities or points should be marked, name them. Describe marker style (dots, pins, pulsing circles) and whether labels appear next to them.
- **Describe lines and routes** -- if the scene shows a route, flight path, or connection between locations, name the start and end points and whether the line is straight, curved (flight arc), or follows a road.
- **Describe animation sequence** -- what happens first, second, third. Does the map start zoomed out then zoom into a country? Do highlights appear one by one or all at once? Do markers pop in with a stagger?
- **NEVER specify hex colors** -- describe the visual intent ("highlighted in a warm red", "filled with a cool blue", "outlined in the accent color from the art style"). The code agent will choose appropriate colors.

## How to Describe a Map Scene

### Step 1: Map projection and viewport

Start with what the viewer sees -- the geographic scope, map shape (projection), and camera.

**Map projection** describes the shape of the map. Available options:
- **Globe** (default) -- 3D sphere, best for world-level views and dramatic reveals
- **Mercator** -- flat rectangular map, best for zoomed-in street/city level views
- **Natural Earth** -- curved-edge world map with classic atlas aesthetics
- **Equirectangular** -- flat rectangular map with straight latitude/longitude lines

If not specified, globe is used by default.

Examples:
- "A globe view of Earth, slowly rotating to center on the Pacific Ocean. Clean satellite style."
- "A world map in natural Earth projection, centered on the Atlantic so both Americas and Europe/Africa are visible. Clean, minimal style with muted land colors and dark ocean."
- "A flat mercator map of the United States, zoomed to show all 48 contiguous states. Slightly tilted 3D perspective. Minimal style with no road or city labels."
- "A globe view of India zoomed to show all states. Top-down view, clean style."

### Step 2: Highlighted regions

Describe which regions are highlighted and how.

- "Three countries highlighted with a semi-transparent fill: United States in blue, India in green, Brazil in red. All other countries remain in the default muted color."
- "The states of California, Texas, and New York are highlighted with a bold fill color. The remaining states stay muted but visible."
- "Countries light up one by one in sequence: first Japan, then South Korea, then India, each with a 0.5-second delay between them."

### Step 3: Markers and labels

Describe any point markers, city dots, or labels. Two styles of markers are supported:
- **Dot markers with text labels** -- simple colored circles with text labels nearby (default)
- **Custom HTML markers** -- fully custom elements like icons, images, or styled badges with embedded labels

Describe the marker style, size, and label placement.

- "Large pulsing dot markers on San Francisco, New York, London, Tokyo, and Sydney. Each marker has a label with the city name appearing next to it."
- "Small dot markers on each state capital, with the state name as a label."
- "Custom pin markers with city name labels embedded below each pin on New York, London, and Tokyo."

### Step 4: Lines and connections

Describe any routes or connections between points.

- "A curved flight-path arc from San Francisco to Tokyo, drawing itself from west to east over 2 seconds."
- "Straight lines connecting New York to London, London to Dubai, and Dubai to Singapore, appearing in sequence."

### Step 5: Animation

Describe the timing and motion.

- "The map starts zoomed out showing the full world. After 1 second, it smoothly zooms into the United States over 2 seconds. Once zoomed in, the three highlighted states fade in one by one."
- "All country highlights appear simultaneously as the scene begins. Markers pop in with a staggered delay, west to east."
