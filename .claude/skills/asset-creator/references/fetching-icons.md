# Fetching Icons with MCP Tool

## Overview
Use the `mcp__course-tools-mcp__list_icons` tool to fetch the list of icon names.
Use the `mcp__course-tools-mcp__search_icon` tool to fetch SVG content for icons returned by list_icons.

---
## The List Tool

### Parameters
- `library` (optional): Library symbol prefix in lowercase (e.g., `bs`, `fa`, `gi`)
- `name_query` (required): Keyword to filter icon names (case-insensitive)

### Return Format
```json
{
  "result": "IconName1\nIconName2\nIconName3..."
}
```

Returns newline-separated list of matching icon names.

### Usage
Use this tool first to discover available icons before fetching specific SVG content.

---
## The Search Tool

### Parameters
- `icon_name` (required): The exact name of the icon from the list fetched above.

### Return Format
Returns the SVG content as a string:
```json
{
  "result": "<svg>...</svg>"
}
```

## Icon Libraries

| Prefix | Library
| ------ | -----------------
| `Bs`   | Bootstrap Icons
| `Fa`   | Font Awesome 5
| `Fa6`  | Font Awesome 6
| `Gi`   | Game Icons

---

## Search Process

1. **Get icons list** use a relevant keyword to fetch for icons from a relevant library with `mcp__course-tools-mcp__list_icons`.
2. **Search** use the appropriate icon name from the list and get the icons svg using `mcp__course-tools-mcp__search_icon`
3. **Receive SVG** and analyze and understand the structure.

---

## Analyzing Icon Geometry

After fetching an icon, analyze its structure to determine key positions for alignment:

### 1. Identify the ViewBox

```svg
<svg viewBox="0 0 512 512">  <!-- This is a 512x512 icon -->
```

Common viewBox sizes:
- Bootstrap: 16x16
- Font Awesome: 512x512
- Game Icons: 512x512

### 2. Find Attachment Points in Path Data

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

---

## Handling Failed Searches

1. Try alternative keyword to fetch the icon list.
2. Try different library.

---
