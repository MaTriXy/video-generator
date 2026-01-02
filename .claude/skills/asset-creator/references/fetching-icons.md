# Fetching Icons with MCP Tool

<overview>
Use the `mcp__video_gen_tools__search_icons` tool to fetch the list of icon names.
Use the `mcp__video_gen_tools__get_icons` tool to fetch SVG content for icons returned by search_icons.
</overview>

<icon-libraries>
Icon Libraries:

| Prefix | Library         |
| ------ | --------------- |
| `Bs`   | Bootstrap Icons |
| `Fa`   | Font Awesome 5  |
| `Fa6`  | Font Awesome 6  |
| `Gi`   | Game Icons      |

</icon-libraries>

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

| Command   | Meaning                    | Example                                 |
| --------- | -------------------------- | --------------------------------------- |
| `M x,y`   | Move to absolute position  | `M79.238 115.768` → starts at (79, 115) |
| `h value` | Horizontal line (relative) | `h406.15` → moves right 406 units       |
| `l x,y`   | Line to (relative)         | `l-28.51 67.863` → draws line           |

See [viewbox-positioning.md](./references/viewbox-positioning.md) → "Aligning Elements to Icon Attachment Points" for how to transform these coordinates.

</find-attachment-points>

</analyzing-icon-geometry>

---

<handling-failed-searches>

<fallback-strategies>
1. Try alternative keyword to fetch the icon list.
</fallback-strategies>

</handling-failed-searches>

---
