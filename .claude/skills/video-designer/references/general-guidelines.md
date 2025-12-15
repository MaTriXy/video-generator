# General Guidelines

## Coordinate System

```
COORDINATE SYSTEM
Origin: Top-left corner (0, 0)
X-axis: Increases rightward →
Y-axis: Increases downward ↓
Position: Always refers to element's CENTER point

ROTATION
0° = pointing up
Positive = clockwise
Negative = counter-clockwise

EXAMPLE (1920×1080 viewport)
Screen center:        x = 960,  y = 540
Top-center:           x = 960,  y = 100
Bottom-left quadrant: x = 480,  y = 810
Right edge center:    x = 1820, y = 540
```

## Output Schema

Your output must be a valid JSON object matching this schema:
```json
{
  "scene": 0,
  "startTime": 0,
  "endTime": 7664,
  "scene_description": "2-3 sentence summary of the visual narrative",
  
  "video_metadata": {
    "viewport_size": "1920x1080",
    "canvas": {
      "backgroundColor": "#HEXCOLOR"
    },
    "layout": {
      "strategy": "three-column|centered|freeform",
      "description": "Brief description of layout approach",
      "vertical_padding_percent": 10
    }
  },
  
  "elements": [
    {
      "id": "unique_element_id",
      "type": "shape|text|character|icon",
      "content": "CRITICAL: Complete visual specification (see content_field_requirements)",
      "zIndex": 1,
      
      "timing": {
        "enterOn": 0,
        "exitOn": 7664
      },
      
      "animation": {
        "entrance": {
          "type": "pop-in|fade-in|slide-in-left|slide-in-right|draw-on|cut" etc,
          "duration": 300
        },
        "exit": {
          "type": "fade-out|pop-out|slide-out-left|slide-out-right",
          "duration": 200
        },
        "actions": [
          {
            "on": 2000,
            "duration": 500,
            "targetProperty": "styles.states.default.opacity",
            "value": 1,
            "easing": "ease-in-out"
          }
        ]
      },
      
      "styles": {
        "position": {
          "x": 960,
          "y": 540
        },
        "size": {
          "width": 200,
          "height": 200
        },
        "rotation": 0,
        "scale": 1,
        "states": {
          "default": {
            "opacity": 1,
            "fill": "#HEXCOLOR",
            "stroke": "#HEXCOLOR",
            "strokeWidth": 2,
            "fontSize": 48,
            "fontWeight": "700",
            "textAlign": "center",
            "lineHeight": 1.2
          }
        }
      }
    }
  ]
}
```

**Required fields per element:** `id`, `type`, `content`, `zIndex`, `timing`, `styles`
**Optional fields:** `animation` (but recommended for visual engagement)

### CRITICAL: Timing Values Must Be Absolute

**All timing values (`enterOn`, `exitOn`, `action.on`) must use absolute video timestamps, NOT relative scene timestamps.**

Given:
- `scene.startTime = 18192` (absolute video time)
- Audio transcript shows word "dust" at `1777ms` (relative to scene start)

Your timing should be:
```json
"timing": {
  "enterOn": 19969,    // 18192 + 1777 = absolute video time
  "exitOn": 24589      // matches scene.endTime (absolute)
}
```

**Formula:** `absolute_time = scene.startTime + audio_relative_time`

## Content Field Requirements

The `content` field is the most critical part. It must answer ALL of these:

| Aspect | What to Specify | Example |
|--------|-----------------|---------|
| **Shape/Form** | Exact geometry, proportions | "Asymmetrical rounded blob—right lobe shorter, left lobe extends 2x downward" |
| **Visual Details** | Colors, textures, features | "Deep orange center (#E65100) fading to bright orange (#FF9800) edges, 3 subtle lighter spots" |
| **Face/Expression** | If character: eyes, mouth, emotion | "Wide white eyes with violet pupils, V-shaped pink eyebrows angled inward expressing anger" |
| **Position Context** | Where in frame, relative to what | "Centered in belly area of silhouette, taking 75% of belly's width" |
| **Initial State** | Starting appearance | "Begins as small concentrated core at liver's center" |
| **Transformations** | What changes and how | "On inhale: body compresses, eyes shrink, mouth tightens to small 'o'; on exhale: expands, eyes widen, mouth stretches to tall oval" |
| **Interaction** | How it relates to other elements | "Scales at same rate as silhouette to maintain relative position inside belly" |

**Precision Test**: Could someone draw this without seeing the original? If uncertain, add more detail.

## Design Process

### Phase 1: Extract Design System from Example

Before designing anything, analyze the example to establish your style guide:

**1.1 Global Properties**
- Background color
- Layout strategy

**1.2 Color Palette**
List each color with its semantic role:
```
#63cee7 → Background (calm state)
#260d74 → Background (dark/dramatic state)
#E65100 → Character fill (deep)
#FF9800 → Character fill (bright edge)
#FFEB3B → Glow/energy effect
```

**1.3 Typography**
Document font styles and calculate proportional sizes (fontSize ÷ viewport_height).

**1.4 Animation Library**
Document each animation type with duration:
```
pop-in: Xms
fade-in: Xms
scale-grow: Xms
color-transition: Xms
```

**1.5 Visual Personality**
| Attribute | Example's Approach |
|-----------|-------------------|
| Mood | (playful/serious/technical) |
| Shapes | (rounded/sharp, thick/thin strokes) |
| Characters | (Kawaii faces, googly eyes, expressive) |
| Motion | (organic wobbles, breathing animations) |
| Metaphors | (how abstract concepts become visual) |

### Phase 2: Design the New Scene

**2.1 Parse Narrative**
Reconstruct sentences from transcript. Identify:
- Key moments needing visual emphasis
- Natural timing beats for element entrances

**2.2 Identify Elements**
From scene_direction, list:
- Primary elements (must have)
- Supporting elements (enhance clarity)
- Labels/text (identify concepts)

**2.3 Design Each Element**
For every element:
1. Write complete `content` description (see content_field_requirements)
2. Calculate exact position and size
3. Assign zIndex for layer order
4. Set timing synced to transcript
5. Define entrance/exit animations
6. Specify any mid-scene actions

**2.4 Sync to Transcript**
Audio timestamps are relative to scene start. Convert to absolute video time:
```
Audio: "ball" at 4708ms (relative)
Scene: startTime = 7000ms (absolute)
Element enterOn: 7000 + 4600 = 11600ms (absolute, with anticipation)

Audio: "bat" at 5908ms (relative)
Element enterOn: 7000 + 5800 = 12800ms (absolute, with anticipation)
```
**Always add scene.startTime to audio timestamps.**

**2.5 Verify Layout**
Check for overlaps by calculating edges:
```
Element A: center(400, 540), size(200, 300)
  → x: [300, 500], y: [390, 690]
Element B: center(700, 540), size(200, 300)  
  → x: [600, 800], y: [390, 690]
✓ No overlap (A ends at x=500, B starts at x=600)
```