# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with the video-generator-mcp app.

**Location:** `apps/video-generator-mcp/` within the `full-lms` monorepo.
**Companion apps:** `apps/video-generator-api/` (Node.js backend), `apps/video-generator-orchestrator/` (Python orchestrator).

## Project Overview

**video-generator-mcp** is a FastMCP-based Model Context Protocol (MCP) server for video generation workflows. It exposes tools for icon search, SVG path generation, design validation, and media processing. The server is consumed by Claude Code via the `course-tools-mcp` MCP configuration.

**Stack:** Python (FastMCP 2.13.1), Node.js (icon data only), Pydantic for validation.

## Running the Server

```bash
# Development (stdio transport)
python -m scripts.tools_mcp

# Development (HTTP transport, default port 5010)
fastmcp run scripts/tools_mcp.py:mcp --transport http --port 5010

# Production deployment via PM2
./deploy.sh
```

## Build & Install

```bash
# Python dependencies
pip install -r requirements.txt

# Node dependencies (icon libraries only — no build step)
npm install
```

## Rebuilding Icon Index

```bash
python -m scripts.assets.emoji.build_icon_index
```

The icon index is a binary pickle file (`.icon_index.bin`) built from `@iconify/json` and `react-icons` node packages. Rebuild when icon library versions change in `package.json`.

### Node Modules Path Resolution

Defined in `scripts/utility/node_modules.py`. In the monorepo, npm may hoist `@iconify/json` and `react-icons` to the root `node_modules`. The resolution logic:

1. **Source libraries** (`ICONIFY_JSON_PATH`, `REACT_ICONS_PATH`, `ICONIFY_PKG_PATH`) are resolved independently — checks the app's local `node_modules` first, falls back to the monorepo root `node_modules`. Each package can live in a different location.
2. **Built index files** (`INDEX_FILE_PATH`, `LIBRARY_ICONS_FILE_PATH`) are always written to and read from the app's own `node_modules` (`apps/video-generator-mcp/node_modules/`).
3. Paths are resolved **once at import time** (module-level code). Since `build_icon_index.py` runs as a standalone subprocess, each build gets a fresh resolution.

## Architecture

### MCP Server Entry Point

`scripts/tools_mcp.py` — Initializes the FastMCP server, loads config from `scripts/tools_mcp_config.json`, and registers tools via four controllers:

| Controller | Tools | File |
|------------|-------|------|
| **Assets** | `get_asset`, `read_svg`, `describe_images` | `scripts/assets_controller.py` |
| **SVG Gen** | `svg_path`, `merge_paths` | `scripts/svg_gen_controller.py` |
| **Validation** | `validate_json`, `validate_tsx`, `validate_script_with_emotions` | `scripts/validation_controller.py` |
| **Workflow** | `write_file`, `claim_prompt` | `scripts/workflow_controller.py` |
| **Sound Effect** | `generate_sound_effect` | `scripts/sound_effect_controller.py` |

| Tool | Purpose | Notes |
|------|---------|-------|
| `get_asset` | Find and return best matching icon SVGs | Max 10 assets per request, parallel fetch |
| `read_svg` | Read SVG file and return content | Direct file read |
| `describe_images` | Fetch and describe images from URLs via LLM vision | Max 10 URLs, supports raster (PNG/JPEG) and SVG |
| `write_file` | Write content to file | Creates parent directories if missing |
| `svg_path` | Generate SVG path `d` attributes for math curves | 12 equation types |
| `merge_paths` | Combine multiple SVG paths into one | — |
| `validate_json` | JSON syntax validation, optional file write | — |
| `validate_tsx` | TypeScript/React syntax validation (async) | — |
| `validate_script_with_emotions` | Validate script with emotion annotations | — |
| `claim_prompt` | Claim a prompt file for a specific step_type and video_id | Used by orchestrator subagents |
| `generate_sound_effect` | Generate sound effect from text via ElevenLabs, upload to S3, save metadata to MongoDB | Returns `{success, url, time}` |

Note: `get_assets`, `get_assets_v2`, `search_assets` (batch tools), and `edit_file` (stub) exist in code but are currently disabled (commented out).

### Tool Implementations

- **`scripts/assets/`** — Icon search engine, asset providers, and style config
  - `base_asset_provider.py` — Abstract base class for all asset providers
  - `video_style_config.py` — Maps video styles to prioritized icon library lists
  - **`scripts/assets/emoji/`** — Icon search subsystem (used for all non-company-logo asset types)
    - `icon_search_engine.py` — Core search logic: index loading, searching, video style prioritization
    - `icon_search_tool.py` — Public API layer (batch APIs)
    - `emoji_asset_provider.py` — Searches local icon indexes and ranks with LLM
    - `iconify_provider.py` — Reads `@iconify/json` node package
    - `react_icons_provider.py` — Reads `react-icons` node package
    - `build_icon_index.py` — Standalone index builder (runs as subprocess)
  - **`scripts/assets/company_logos/`** — Company logo search via iconify simple-icons + Logo.dev
    - `company_logos_asset_provider.py` — Iconify-first, Logo.dev fallback

- **`scripts/svg_gen/`** — SVG path generation
  - `svg_path_tool.py` — Mathematical SVG path generator (PARABOLIC, CIRCULAR, ELLIPTICAL, SINE_WAVE, SPIRAL, S_CURVE, LINEAR, ARC, BEZIER, ZIGZAG, BOUNCE, SPLINE)
  - `merge_paths_tool.py` — Merges multiple SVG paths into one

- **`scripts/validation/`** — Design and code validation
  - `validate_json_tool.py` — JSON syntax validation
  - `validate_tsx_tool.py` — TypeScript/React validation with runtime checks
  - `validate_script_with_emotions_tool.py` — Script with emotions annotation validation
  - `remotion_render_validator.mjs` — Node.js runtime validator for Remotion components

- **`scripts/tools/`** — Additional tool implementations
  - `prompt_claim_tool.py` — Implementation for `claim_prompt` tool

### Utility Layer

- `scripts/logging_config.py` — Centralized logging with process-isolated log files, `[PREFIX]` convention (e.g., `[GET_ICONS]`, `[SEARCH_ICONS]`)
- `scripts/utility/file_io.py` — File write operations used by validation tools

### Claude Code Integration

- `.claude/settings.json` — Permissions, MCP server config, and SubagentStop hook
- Skills referenced: `asset-creator`, `video-coder`, `video-creator`, `video-designer`, `video-director`

## Key Patterns

- **Eager index loading:** All 10,000+ icon indexes are loaded at module import time, not on first request. Changes to index loading affect server startup time.
- **Batch asset fetching:** `get_asset` accepts an array of up to 10 `{name, description}` objects and fetches all in parallel via `asyncio.gather`. Each asset is AI-matched against search candidates independently.
- **Default icon color:** Icons are fetched with `color='#000'` by default. AI-generated SVG descriptions include color info (multicolor vs monotone) and background suitability.
- **Video style prioritization:** Icon search results are reordered based on `video_style_config.json` library rankings per style. Primary libraries rank higher than secondary.
- **Binary pickle indexes:** Icon indexes are stored as `.icon_index.bin` files for fast deserialization. Version checking uses package.json hashes to detect staleness.
- **Monorepo dependency resolution:** Icon libraries are resolved via `scripts/utility/node_modules.py` (local first, then root). `validate_tsx` and `remotion_render_validator.mjs` resolve TypeScript compiler and Remotion from the monorepo root `node_modules` (npm workspaces hoists packages).
- **Logging convention:** All log messages use bracketed prefixes: `[COURSE_TOOLS_MCP]`, `[GET_ASSET]`, `[SVG_PATH]`, `[VALIDATE_*]`, `[ICON_INDEX]`.

## Environment

Key variables:
- `ENV` — `dev`/`prod`, controls logging verbosity
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` — LLM access
- `ELEVENLABS_API_KEY` — ElevenLabs API key for sound effect generation
