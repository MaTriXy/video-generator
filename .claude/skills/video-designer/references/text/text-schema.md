# Text Element Schema

   ## Schema Structure

   ```json
   {
       "id": "Unique identifier for this text element",
       "type": "Element type must be text",
       "content": "Brief description of what this text represents or its purpose in the scene",
       "text": "The actual text content to display",
       "bgID": "ID of parent/background element - ONLY for positioning text ON diagram elements (optional)",
       "zIndex": "Layering order for overlapping elements",

       "timing": {
         "enterOn": "ABSOLUTE video time in ms (scene.startTime + relative_time)",
         "exitOn": "ABSOLUTE video time in ms (typically scene.endTime)"
       },

       "animation": {
         "entrance": {
           "type": "Entry animation style (pop-in|fade-in|slide-in-left|slide-in-right|draw-on|cut)",
           "duration": "Entry animation duration in milliseconds"
         },
         "exit": {
           "type": "Exit animation style (pop-in|fade-in|slide-in-right|draw-on|cut)",
           "duration": "Exit animation duration in milliseconds"
         }
       },

       "container": {
         "padding": "Spacing around text in pixels - makes background auto-fit text size (required)",
         "background": {
           "type": "Background style: none|solid|gradient|frosted-glass|highlight",
           "color": "Fill color - hex code or color name",
           "opacity": "Background transparency 0-1",
           "gradient": {
             "from": "Starting gradient color (required if type is gradient)",
             "to": "Ending gradient color (required if type is gradient)",
             "direction": "Gradient direction: to-right|to-left|to-bottom|to-top|to-br|to-bl"
           }
         },
         "border": {
           "radius": "Rounded corners in pixels",
           "color": "Border color - hex code or color name",
           "width": "Border thickness in pixels"
         },
         "backdropBlur": "Blur amount for frosted-glass effect: sm|md|lg|xl (optional, only used with frosted-glass type)"
       },

       "styles": {
         "position": {
           "x": "Horizontal position in pixels from left",
           "y": "Vertical position in pixels from top"
         },
         "rotation": "Rotation angle in degrees (0-360)",
         "states": {
           "default": {
             "opacity": 1,
             "fontColor": "Font Color",
             "fontSize": "Text size in pixels (required)",
             "textAlign": "Horizontal alignment: left, center, right (required)",
             "fontWeight": "Text boldness level",
             "lineHeight": "Vertical spacing between multiple text lines"
           }
         }
       }
     }
   ```

   ---
  ```json
  {
    "id": "code_example_label",
    "type": "text",
    "content": "Label displaying code example with gradient background",
    "text": "Hello World!",
    "bgID": "",
    "zIndex": 5,

    "timing": {
      "enterOn": 1000,
      "exitOn": 5000
    },

    "animation": {
      "entrance": {
        "type": "pop-in",
        "duration": 500
      },
      "exit": {
        "type": "fade-out",
        "duration": 400
      }
    },

    "container": {
      "padding": 20,
      "background": {
        "type": "gradient",
        "color": "#3B82F6",
        "opacity": 0.9,
        "gradient": {
          "from": "#3B82F6",
          "to": "#8B5CF6",
          "direction": "to-right"
        }
      },
      "border": {
        "radius": 12,
        "color": "#FFFFFF",
        "width": 2
      },
      "backdropBlur": "md"
    },

    "styles": {
      "position": {
        "x": 960,
        "y": 540
      },
      "rotation": 0,
      "states": {
        "default": {
          "opacity": 1,
          "fontColor": "#FFFFFF",
          "fontSize": 42,
          "textAlign": "center",
          "fontWeight": 700,
          "lineHeight": 1.4
        }
      }
    }
  } 
  ```

   ## Key Points

   1. **Auto-fit backgrounds**: When using container.background, the background automatically sizes to fit the text + padding
   2. **bgID is for diagrams only**: Use bgID ONLY for positioning text ON other diagram elements, NOT for backgrounds
   3. **Padding makes backgrounds auto-size**: The container.padding property creates spacing and makes the background fit perfectly
   4. **Multiple background types**: Choose from none, solid, gradient, frosted-glass, or highlight based on your design needs
   5. **No separate shape elements needed**: Text backgrounds are built into the text element itself
   EOF