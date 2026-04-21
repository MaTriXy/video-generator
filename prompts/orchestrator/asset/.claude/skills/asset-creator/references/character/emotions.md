# Character Emotions

<overview>
Characters can express **any emotion** the scene demands. Use whatever facial features, body language, and visual cues best convey the emotion. The ideas below are just starting points — not rules.
</overview>

<expressive-tools>

Ways to convey emotion (use any combination):

- **Eyes** — size, shape, pupil position, squinting, wide-open, half-closed, eye shine, tears
- **Eyebrows** — angle, curve, thickness, position
- **Mouth** — smile, frown, open, teeth, tongue, wavering, smirk
- **Cheeks** — blush, flush, color shifts
- **Body language** — posture, gesture, limb positioning, leaning
- **Extras** — tears, sweat drops, zzz, sparkles, steam, exclamation marks, motion lines, aura/glow

</expressive-tools>

---

<eye-blink-animation>

<blink-technique>
One approach for eye blink using **clipPath** (pupils get clipped, not squished):

```svg
<defs>
  <clipPath id="leftEyeClip">
    <ellipse cx="95" cy="115" rx="14" ry="16">
      <animate attributeName="ry" values="16;16;0;0;16;16" keyTimes="0;0.47;0.49;0.51;0.53;1" dur="3s" repeatCount="indefinite"/>
    </ellipse>
  </clipPath>
</defs>

<!-- Eye white -->
<ellipse cx="95" cy="115" rx="14" ry="16" fill="white">
  <animate attributeName="ry" values="16;16;0;0;16;16" keyTimes="0;0.47;0.49;0.51;0.53;1" dur="3s" repeatCount="indefinite"/>
</ellipse>
<!-- Pupil clipped by eye shape -->
<circle cx="98" cy="115" r="7" fill="#1a1a1a" clip-path="url(#leftEyeClip)"/>
```
</blink-technique>

<blink-explanation>
**How it works:** Eye white animates `ry` from full to 0 and back. ClipPath contains the same animated ellipse to clip the pupil. The pupil itself doesn't animate — it's masked by the clipPath.
</blink-explanation>

Adapt coordinates, sizes, timing, and duration to fit whatever character you're building. This is a reference technique, not a fixed template.

</eye-blink-animation>
