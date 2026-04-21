# Multi-Element Layout Scenes

## When to use
Read this file when the script involves lists of items, grids, mind maps, radial arrangements, many elements needing spatial organization, or scenes where multiple objects must be arranged on screen without overlapping. Also useful when the script mentions categories, types, or enumerations of things.

<examples>

<example_1>
"audioTranscriptPortion": "And all of these costs shift depending on card type, country, and whether it's a basic debit card or a premium rewards card.",
"videoDescription": "Bars fade out completely. An 8x6 grid of payment cards fills the frame, entering with a diagonal 'rainfall' cascade (top-left to bottom-right, each card dropping from slightly above). Three hero featured cards break out of the grid: DEBIT (upper-left quadrant), CREDIT (center), PREMIUM (upper-right quadrant, with star icon). Featured cards spring in from scale-zero to full size, staggered sequentially. As narration mentions each card type, that card highlights -- scaling up to roughly 1.35x with border thickening, creating a sequential spotlight effect. 'COSTS SHIFT BY CARD TYPE' appears centered at the bottom, sliding up from below."
</example_1>

<example_2>
"audioTranscriptPortion": "Apple devices are all over the world. And by 2030, all of the electricity charging all of your devices will be 100% renewable.",
"videoDescription": "A sketch of the @earth_sketch spins at the bottom of the screen. Text reads \"And by\" followed by a fixed-width number slot. Numbers (2024, 2025, 2026, 2027, 2028, 2029) flip vertically through the slot rapidly, like a slot machine. The slot has a fixed bounding box so the surrounding text does not shift. The counter lands on \"2030\". The number slot should be inline with \"And by\" on the same baseline. A @lightning_icon appears inside a circle of dots. Center text \"all of your devices\" remains fixed at screen center. Product names (iPhone, AirPods, HomePod, MacBook, iPad, Apple Watch, Apple TV, iMac) appear at positions radiating outward from center, evenly distributed. Thin arrows point from each product name toward the center text. Product names must NOT overlap each other -- maintain enough gap between bounding boxes to keep all text readable. Arrows MAY cross each other. The center text sits on a higher z-index so product names and arrows render behind it, never covering it. \"will be 100% renewable.\" text glows."
</example_2>

<example_3>
"audioTranscriptPortion": "That project, along with other hundred prototypes, is the reason I started building a framework. I've split this into three phases, and honestly each one is just a different way of asking \"should we keep going or kill this thing right now.\"",
"videoDescription": "96 small dots fade in, randomly spread across the entire screen, away from each other. All drift gently. On 'framework', the dots smoothly transition into three equal column groups with 32 dots in each group, arranged in a grid -- dots that started on the left move to the center or right group, dots from the center move to the left or right group, and dots from the right move to the left or center group, so each dot travels away from its starting zone to reach its final position. The three groups occupy roughly 80% of the screen width, centered on screen with equal spacing. Phase labels appear above each group: 'PRE-PRODUCTION', 'PRODUCTION', 'VALIDATION'. On 'should we keep going or kill this thing right now', a traffic-light bar appears below each group -- a thin strip that oscillates between signaling go and stop, representing the keep-going-or-kill decision at each phase."
</example_3>

</examples>
