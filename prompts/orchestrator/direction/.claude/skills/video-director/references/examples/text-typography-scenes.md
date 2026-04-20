# Text & Typography Scenes

## When to use
Read this file when the script calls for text-dominant scenes -- kinetic typography, word-by-word reveals, character-by-character typing, editorial corrections (caret insertions), inline logo/icon replacements within text, or scenes where animated text IS the primary visual element rather than supporting element.

<examples>

<example_1>
"audioTranscriptPortion": "Apple has a plan. And a promise.",
"videoDescription": "Minimalist, centered text with a logo element. The standard @apple_logo but with a leaf pops in first, slightly to the left of the center. Primary text \"has a plan.\" in bold sans-serif font appears word-by-word (\"has\", then \"a\", then \"plan\") to the right of the logo. The logo and text are on the same horizontal baseline, forming a single inline sentence that reads as: [logo] has a plan. There should be a small gap between the logo and the text. Secondary text \"AND A PROMISE.\" in handwritten marker-style font, all caps. The period at the end of \"plan\" morphs into a small arrow head pointing up. Then the entire [logo + \"has a plan\"] group shifts left as a single unit. \"AND A PROMISE.\" writes itself in on the right side of the screen. All three elements (logo, primary text, secondary text) share the same horizontal baseline and remain in a single row with no vertical stacking. Narration-to-Action Mapping: \"Apple has a plan.\" syncs with the text appearing word-by-word. \"And a promise.\" syncs with the handwritten text appearing."
</example_1>

<example_2>
"audioTranscriptPortion": "To make Apple carbon neutral... wait, no. We've already done that.",
"videoDescription": "Rapid text cuts followed by a checklist UI element. Text \"To make [@apple] carbon neutral\" flashes briefly on screen before cutting. Text \"wait\" is replaced instantly by \"no\" in sans-serif centered. A square @checkbox_outline appears on the left edge. To its right, \"we\" morphs into \"we've\" on the same baseline. \"ALREADY\" appears in handwritten font between \"we've\" and \"done that\" -- inserted inline, not floating above. All elements sit on one horizontal line: [checkbox] we've ALREADY done that. A checkmark animates swiftly into the @checkbox_outline. Narration-to-Action Mapping: \"Wait, no.\" visuals cut, text swaps rapidly to match the interruption. \"We've already done that.\" the checkmark ticks the box exactly on the phrase \"done that.\""
</example_2>

<example_3>
"audioTranscriptPortion": "To make every single Apple product carbon neutral by 2030.",
"videoDescription": "Centered kinetic typography filling the screen. Text flashes: \"To make\", \"To make ev\", \"To make ever\", \"To make every\" -- typing on rapidly, character by character. Text \"single [] product\" where the @apple_logo replaces the [] and sits inline between \"single\" and \"product\" on the same text baseline. The logo should be vertically centered with the text. Small spark lines radiate outward from the logo's center but must NOT extend far enough to touch the words \"single\" or \"product\". The sparks are a decorative overlay layer rendered above the text layer. Text \"carbon neutral by 2030.\" where \"carbon\" slides left to reveal \"neutral\". Then \"by 2030\" appears. A handwritten-style underline draws itself directly beneath the word \"2030\", with a small vertical gap. The underline width matches the text width of \"2030\" and does not extend beyond it. Narration-to-Action Mapping: \"Every single...\". \"...2030.\" the underline draws exactly when the date is spoken."
</example_3>

<example_4>
"audioTranscriptPortion": "But we can do much MORE. It's not just what goes into our products. It's also how they're made. Hundreds of manufacturers, distributors, testers, assemblers, dis-assemblers, material-makers...",
"videoDescription": "Typography explosion followed by a Mind Map. \"MORE.\" appears in massive bubble-style letters, centered on screen. The @factory_icon is positioned at the exact center of the letter 'O' in \"MORE\", sized to fit inside the letter's counter (the hollow space). This is intentional -- the icon sits INSIDE the letter. Smoke puffs animate upward from the factory's smokestack, rising above the top edge of the 'O'. The smoke is a foreground layer that intentionally overlaps the top of the letter. Text \"It's not just what\" (underline) then \"goes into our products.\" Text \"it's also how\" where the letter 'O' in the word \"how\" is replaced by a gear/cog icon of the same size as the letter. The gear spins continuously in place. The gear occupies the exact same bounding box as the original 'O'. Then \"they're made.\" (underline on HOW). The mind map starts from a center node \"Hundreds of\". Each new word (\"manufacturers\", \"distributors\", \"testers\", \"assemblers\", \"dis-assemblers\", \"material-makers\") appears at a calculated position radiating outward from center, evenly distributed around 360 degrees. Arrows connect center to each word. Words must NOT overlap each other -- maintain enough gap between any two word bounding boxes to keep all text readable. Arrows MAY cross each other -- this is intentional and adds to the \"complex web\" feel."
</example_4>

</examples>
