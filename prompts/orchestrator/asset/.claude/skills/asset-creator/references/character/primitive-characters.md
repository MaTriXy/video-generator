# Character Creation

<style-reference>
> **Style:** Friendly, expressive, visually appealing. Any style works — simple geometric mascots, detailed illustrated characters, cartoon-style figures, stick figures, realistic proportions, chibi, etc. Match the style to the scene's needs.
</style-reference>

<character-structure>

Characters can be built however best suits the scene. There are no restrictions on body structure — use any combination of shapes, body parts, and proportions.

**Common approaches (not requirements):**
- Simple geometric body with face (mascot-style)
- Full-body character with head, torso, arms, legs
- Stylized/abstract figure
- Animal or creature with any anatomy needed
- Personified object with a face

Use whatever body structure makes sense for the character being created.

</character-structure>

---

<before-drawing>
1. **What kind of character?** — human, animal, robot, object, abstract, etc.
2. **Orientation?** — forward, left, right, 3/4 view
3. **Emotion?** — affects facial expression (see [emotions.md](./emotions.md))
4. **Action/pose?** — standing, sitting, running, holding something, etc.
5. **Level of detail?** — simple icon-like or more detailed illustration

</before-drawing>

---

<body-parts>

Characters can have any body parts needed:
- Head (separate or combined with body)
- Torso / body
- Arms, hands, fingers
- Legs, feet
- Tails, wings, horns, antennae
- Hair, hats, accessories
- Any other anatomical or stylistic features

There are no restrictions — add whatever the character needs to look right and serve the scene.

</body-parts>

<objects-and-props>
Characters can interact with objects in any way:
- Hold items in hands
- Carry things on their back
- Wear accessories
- Have objects floating nearby
- Any interaction that makes visual sense

</objects-and-props>

---

<non-human-characters>

**Non-Human Characters** (robots, animals, creatures):
- Use whatever structure suits the character type
- Animals can have four legs, tails, ears, snouts — whatever is anatomically appropriate
- Robots can have mechanical parts, antennas, panels, joints
- Keep the character recognizable and expressive
- Make sure the viewbox is big enough to show the full character

<personified-objects>
**Personified Objects** (objects given personality):
- Keep the object's original form recognizable
- Add face/expressions as needed
- Can optionally add limbs or other features if it helps the scene
</personified-objects>

</non-human-characters>

---

<core-rules>

<emotion-eye-animation>
**Emotion & Eye Animation**
Characters should have:
1. **A relevant emotion** - Choose expression based on scene context (happy, sad, angry, surprised, sleepy, etc.)
2. **Eye blinking animation** - Preferably include clipPath-based eye blink (see [emotions.md](./emotions.md))

</emotion-eye-animation>

<scaling>
**Scaling**
- Characters can be rendered at any size
- Use CSS/SVG transforms to scale
</scaling>

<colors>
**Colors**
- Use vibrant, appealing colors that suit the character
- Eye and mouth colors are flexible — use whatever looks good
- No color restrictions
</colors>

</core-rules>

---

<standard-specifications>
**ViewBox:** `0 0 250 250` (minimum 250×250, character must be centered and fully visible)

**Layer Order (SVG render order):**
1. Back elements (tail, wings, shadow, etc.)
2. Body
3. Face features (eyes, mouth, etc.)
4. Front elements (arms in front, accessories, etc.)

</standard-specifications>

---

<examples>
No fixed examples — design each character to fit the scene. Simple or detailed, geometric or organic, minimal or complex. Whatever serves the visual best.
</examples>

<emotions-reference>
For character emotions and expressions, see [emotions.md](./emotions.md).

</emotions-reference>
