# Object Interaction Scenes

## When to use
Read this file when the script involves physical objects moving through space, emitting signals, connecting to each other, morphing into different shapes, or mechanically interacting. These are scenes built around assets/objects as the primary visual -- not UI mockups, not text, not charts.

<examples>

<example_1>
"audioTranscriptPortion": "We're working to make every iPhone, iPad, Watch, and Mac with 100% recycled or renewable materials.",
"videoDescription": "Text bottom-center, animated icons center. A neon outline drawing starts as an @iphone_outline (labeled 'iPHONE'). Instantly morphs into an @ipad_outline (labeled 'iPAD'). Morphs into an @watch_outline (labeled 'WATCH'). Morphs into a @mac_outline (labeled 'MAC'). Text 'We're working' then 'to make every...' then text below the icon changes to 'with 100% recycled'. This uses an 'editorial correction' layout with two vertical layers: BOTTOM LAYER: The main sentence 'with 100% recycled' in sans-serif. TOP LAYER: A caret ^ symbol positioned directly above 'recycled', centered on it. Above the caret, 'OR RENEWABLE' appears in handwritten font, also centered above 'recycled'. There should be a clear vertical gap between the two layers. The caret and handwritten text must not overlap the device icon area above them or the bottom sentence text below. Narration-to-Action Mapping: 'iPhone, iPad, Watch...' the icon morphs exactly on the beat of each product name. 'or renewable' the text is inserted like a correction on a document."
</example_1>

<example_2>
"audioTranscriptPortion": "We're finding new ways to extract aluminum, steel, tin, tungsten, plastic from recycled Apple products.",
"videoDescription": "Intro text 'We're finding new ways' appears surrounded by motion sparks. A line-drawing of a @claw_arm enters from above the top edge of the viewport and lowers vertically downward toward center screen. The claw is rendered on a foreground layer ABOVE any text. If 'to extract' text is visible, the claw may pass over it -- this is intentional. The claw should be horizontally centered on screen. Material footage rapid cuts: @aluminum_shreds with text overlay 'aluminum'. @steel_press with text overlay 'steel'. @tin_granules with text overlay 'tin'. @tungsten_arm with text overlay 'tungsten'. @plastic_shreds with text overlay 'plastic'. Then text 'from recycled [] products.' where the word 'recycled' is displayed, then individual letters morph in-place into icons: 'r' becomes a Recycle symbol, 't' becomes a Tree icon, 'l' becomes a Leaf icon. Each icon occupies the exact same bounding box as the letter it replaces -- same position, same approximate size. The remaining letters that don't transform stay as text. This is intentional same-position replacement, not side-by-side placement."
</example_2>

</examples>
