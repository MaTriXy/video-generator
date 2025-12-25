# Fetching Icons with MCP Tool

<overview>
Use the `mcp__video_gen_tools__search_icons` tool to fetch the list of icon names.
Use the `mcp__video_gen_tools__get_icon` tool to fetch SVG content for icons returned by search_icons.

</overview>

---

<search-tool>

<search-parameters>
Parameters:
- `library` (optional): Library symbol prefix in lowercase (e.g., `bs`, `fa`, `gi`)
- `name_query` (required): Keyword to filter icon names (case-insensitive)

</search-parameters>

<search-return-format>
Return Format:
```json
{
  "result": "IconName1\nIconName2\nIconName3..."
}
```

Returns newline-separated list of matching icon names.

</search-return-format>

<search-usage>
Use this tool first to discover available icons before fetching specific SVG content.

</search-usage>

</search-tool>

---

<get-tool>

<get-parameters>
Parameters:
- `icon_name` (required): The exact name of the icon from the list fetched above.

</get-parameters>

<get-return-format>
Returns the SVG content as a string:
```json
{
  "result": "<svg>...</svg>"
}
```

</get-return-format>

</get-tool>

<icon-libraries>
Icon Libraries:

| Prefix | Library
| ------ | -----------------
| `Bs`   | Bootstrap Icons
| `Fa`   | Font Awesome 5
| `Fa6`  | Font Awesome 6
| `Gi`   | Game Icons

</icon-libraries>

---

<search-process>

<search-steps>
1. **Get icons list** use a relevant keyword to fetch for icons from a relevant library with `mcp__video_gen_tools__search_icons`.
2. **Search** use the appropriate icon name from the list and get the icons svg using `mcp__video_gen_tools__get_icon`
3. **Receive SVG** and analyze and understand the structure.
</search-steps>

</search-process>

---

<analyzing-icon-geometry>
After fetching an icon, analyze its structure to determine key positions for alignment:

<identify-viewbox>
**1. Identify the ViewBox**

```svg
<svg viewBox="0 0 512 512">  <!-- This is a 512x512 icon -->
```

Common viewBox sizes:
- Bootstrap: 16x16
- Font Awesome: 512x512
- Game Icons: 512x512

</identify-viewbox>

<find-attachment-points>
**2. Find Attachment Points in Path Data**

Examine path commands to identify key coordinates:

```svg
<path d="M79.238 115.768l-28.51 67.863h406.15..."/>
```

| Command | Meaning | Example |
|---------|---------|---------|
| `M x,y` | Move to absolute position | `M79.238 115.768` → starts at (79, 115) |
| `h value` | Horizontal line (relative) | `h406.15` → moves right 406 units |
| `l x,y` | Line to (relative) | `l-28.51 67.863` → draws line |

See [viewbox-positioning.md](./references/viewbox-positioning.md) → "Aligning Elements to Icon Attachment Points" for how to transform these coordinates.

</find-attachment-points>

</analyzing-icon-geometry>

---

<handling-failed-searches>

<fallback-strategies>
1. Try alternative keyword to fetch the icon list.
2. Try different library.
</fallback-strategies>

</handling-failed-searches>

---
