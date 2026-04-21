# OVG — Outscal Video Generator

> **Getting started?** Ask your coding agent (Claude Code) to read this
> `README.md` end-to-end and set up the project for you. It will install the
> Python and Node dependencies, guide you through filling in `.env`, and
> verify the pipeline is ready to run.

OVG is a Claude-Code-driven pipeline that turns a topic, brief, or raw
narration into an animated [Remotion](https://www.remotion.dev/) video you can
preview locally in your browser. Five specialized sub-agents — script,
direction, audio, assets, code — collaborate under a Claude Code
*orchestrator* that reviews each step's output, loops back to fix weak scenes,
and only moves forward when the work clears the quality bar.

---

## Table of contents

1. [Prerequisites](#prerequisites)
2. [One-time setup](#one-time-setup)
3. [How video generation works (end-to-end)](#how-video-generation-works-end-to-end)
4. [Generating a video](#generating-a-video)
5. [Previewing and rendering](#previewing-and-rendering)
6. [Regenerating a single scene](#regenerating-a-single-scene)
7. [Project layout](#project-layout)
8. [CLI reference](#cli-reference)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.13**
- **Node.js 18+** — for the Remotion Studio preview and the iconify asset index
- **Claude Code** installed and authenticated ([install guide](https://docs.claude.com/en/docs/claude-code/overview))
- **API keys** — at minimum:
  - An Anthropic Claude Code OAuth token (`sk-ant-oat01-...`) — get it via `claude setup-token`
  - An [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) API key for narration TTS
  - Optional: a [Mapbox](https://account.mapbox.com/access-tokens/) token if any scene renders a map

  See [`example.env`](./example.env) for the full list with links and defaults.

## One-time setup

From the repo root:

```bash
# 1. Configure secrets
cp example.env .env
#   then edit .env and fill in the keys

# 2. Python deps for the orchestrator pipeline
pip install -r requirements.txt

# 3. Python deps for the tools CLI (asset fetching, validation, TTS, SFX)
pip install -r video-tools/requirements.txt

# 4. Node deps for the iconify icon library (used by the asset agent)
cd video-tools && npm install && cd ..

# 5. Node deps for the Remotion Studio preview
cd studio && npm install && cd ..
```

---

## How video generation works (end-to-end)

OVG is built around two ideas:

1. **A Claude Code orchestrator drives the pipeline.** Inside your Claude Code
   session, the model reads `.claude/CLAUDE.md` and acts as a creative director.
   It does not blindly run a fixed workflow — it spawns specialized sub-agents,
   reviews their output against a quality bar, and loops back to fix weak work
   before moving on.
2. **The actual work runs as plain Python CLIs and Remotion code.** No MCP
   server, no hidden services. Two CLIs do all the heavy lifting:

   | CLI | Run from | Purpose |
   |---|---|---|
   | `python -m scripts.cli_pipeline <subcommand>` | OVG root | Pipeline orchestration: `init`, per-step `pre`/`post`, `info`, `prompts` |
   | `python -m scripts.tools_cli <subcommand>`    | `video-tools/` | Worker tools: SVG/icon fetching, JSON/TSX validation, math-based SVG paths, sound effects |

The pipeline produces, **for each topic**, a self-contained folder under
`Outputs/{TOPIC}/` that holds the script, the manifest, the scene-by-scene
direction JSON, the narration MP3, the per-scene frame timestamps, all SVG/PNG
assets, every generated Remotion scene component, and the final composition
file Remotion Studio plays.

### The five sub-agents

Each sub-agent is a focused Claude Code agent defined in `.claude/agents/*.md`.
The orchestrator spawns them via the Task tool. Every sub-agent owns its full
step end-to-end (its own `pre` and `post` runs) — the orchestrator never calls
`cli_pipeline pre`/`post` directly.

| # | Sub-agent | Input | What it does | Output |
|---|---|---|---|---|
| 0 | `script-agent` | Topic / brief / raw user input | Drafts a voiceover script, self-rates it on 9 dimensions, revises until it scores 9.0+ (max 5 passes) | `Outputs/{TOPIC}/script.md` |
| 1 | `direction-agent` | The script + style + ratio | Splits the script into scenes; for each scene writes a self-contained `videoDescription` (cinematic, no humans, no implementation details). Declares all `required_assets`. | `Outputs/{TOPIC}/Direction/Latest/latest.json` |
| 2 | `audio-agent` | The script | Inserts ElevenLabs emotion tags (`[curious]`, `[deadpan]`, `[pause]`, ...) without changing any words. The post step then synthesizes the MP3 via ElevenLabs and writes a per-scene frame-timestamp transcript back into the direction JSON. | `Outputs/{TOPIC}/Audio/latest.mp3`, `Outputs/{TOPIC}/Transcript/latest.json` |
| 3 | `asset-agent` | `required_assets` from direction | Picks the right kind of asset for each name (`emoji`, `illustration`, `human-character`, or `company-logo`) and fetches it via `tools_cli get_asset`. Falls back to creating a clean SVG from scratch only if nothing suitable is found. | SVG/PNG files in `Outputs/{TOPIC}/Assets/Latest/`, mirrored into `Outputs/{TOPIC}/public/` for Remotion |
| 4 | `code-agent` | All previous outputs | Reads one prompt per scene (auto-generated with frame ranges from the transcript), writes a Remotion TSX component per scene, validates them in batch, and stitches them into a single Remotion composition. | `Outputs/{TOPIC}/Video/Latest/scene_{i}.tsx` and `composition.tsx` |

### The orchestration flow

```
            you say
"make a video about how WiFi works"
              │
              ▼
   ┌────────────────────────┐
   │  script-agent          │  draft → self-rate → revise (up to 5 passes)
   │  ─────────────────     │  produces: Outputs/{TOPIC}/script.md
   └────────────────────────┘
              │
              ▼
   ┌────────────────────────┐
   │  cli_pipeline init     │  creates manifest.json, picks viewport
   │  --topic --script      │  from style + ratio (vox/9:16/etc.)
   │  --style --ratio       │
   └────────────────────────┘
              │
              ▼
   ┌────────────────────────┐
   │  direction-agent       │  pre  → reads prompt, examples, hooks rules
   │                        │  gen  → scene-by-scene JSON
   │                        │  post → versions, extracts narration
   └────────────────────────┘  ◄──── orchestrator reviews each scene;
              │                       weak scenes get re-spawned
              ▼
   ┌────────────────────────┐
   │  audio-agent           │  pre  → loads script
   │                        │  tag  → adds [emotion] tags
   │                        │  post → ElevenLabs TTS → MP3 +
   │                        │         per-scene frame timestamps
   └────────────────────────┘
              │
              ▼
   ┌────────────────────────┐
   │  asset-agent           │  pre  → reads required_assets
   │                        │  fetch → tools_cli get_asset (iconify,
   │                        │          react-icons, simple-icons,
   │                        │          Logo.dev for company logos)
   │                        │  post → mirrors to public/ for staticFile()
   └────────────────────────┘  ◄──── orchestrator can re-run
              │                       a subset by asset name
              ▼
   ┌────────────────────────┐
   │  code-agent            │  pre  → builds one prompt_{i}.md per scene
   │                        │         using transcript frame ranges
   │                        │  gen  → all scene_{i}.tsx in one batch
   │                        │  validate via tools_cli validate_tsx
   │                        │  post → writes composition.tsx
   └────────────────────────┘  ◄──── orchestrator can re-spawn for
              │                       a single scene index
              ▼
        python studio.py {TOPIC}
              │
              ▼
   browser preview at http://localhost:3000
```

### Why the orchestrator can loop back

Because each artifact lives at a stable path under `Outputs/{TOPIC}/`, any step
can be re-run after editing a previous step's output. The most common loops:

- **Script ↔ Script** — opening flat, closer summarises → re-spawn `script-agent` with feedback.
- **Direction ↔ Direction** — a few weak scenes → re-spawn `direction-agent` with the specific scene indices.
- **Assets → Direction** — an asset can't be cleanly fetched/created → change the direction so it doesn't need that visual.
- **Code → Direction** — a TSX scene reveals the direction was too vague → tighten the direction → re-run code for that one scene.

Every re-run is targeted: the agents support regenerating a subset of scenes
or assets without touching the rest.

### Quality bar (what the orchestrator rejects)

The orchestrator reads every direction JSON before passing it on. Common
rejection causes (full list in `.claude/CLAUDE.md`):

- Humans, body parts, faces, or human silhouettes.
- Implementation details (hex colors, pixel values, easings).
- Scenes that reference each other ("same as scene 2").
- Vague descriptions that aren't visually specific.
- Static or empty backgrounds — backgrounds must "breathe".
- Scene 0 that doesn't stop the scroll (no hero element >50% screen, no mid-action first frame).
- Orphaned `@assets` or missing `required_assets`.
- Non-ASCII characters anywhere in the JSON.

---

## Generating a video

Open the project in Claude Code from the OVG root (`claude` from
`C:\Outscal\video-generator`) and just describe what you want. Two common
patterns:

### Path A — start from a topic

In the Claude Code chat, say:

> Generate a video for `how-wifi-works-v2`. Topic: how home WiFi actually
> works. Portrait, vox style.

The orchestrator will:

1. Spawn `script-agent` to draft the narration (saved to `Outputs/how-wifi-works-v2/script.md`).
2. Run `python -m scripts.cli_pipeline init --topic how-wifi-works-v2 --script Outputs/how-wifi-works-v2/script.md --style vox --ratio 9:16`.
3. Spawn `direction-agent`, then `audio-agent`, then `asset-agent`, then `code-agent` in order, reviewing each step.

### Path B — start from your own script

If you already have polished narration:

1. Save it to `Outputs/{TOPIC}/script.md` (where `{TOPIC}` is a slug ending in `-v2`, e.g. `how-wifi-works-v2`).
2. From the OVG root run:

   ```bash
   python -m scripts.cli_pipeline init \
     --topic how-wifi-works-v2 \
     --script Outputs/how-wifi-works-v2/script.md \
     --style vox \
     --ratio 9:16
   ```

   - `--style` — one of `4g5g | brutalism | glitch-art | memphis | neobrutalism | risograph | synthwave | typography-apple | vox`
   - `--ratio` — `9:16` (portrait, 1080×1920) or `16:9` (landscape, 1920×1080)
   - `--voice-id` — optional ElevenLabs voice ID override

3. In the Claude Code chat, say: *"Generate the video for `how-wifi-works-v2`."*
   The orchestrator picks up from the direction step.

### What you'll see while it runs

Each sub-agent prints short progress messages and ends with one of:

- `Script complete` / `Direction complete` / `Audio complete` / `Assets complete` / `Code complete`
- `... failed: <reason>`

Between steps, the orchestrator reads the produced files itself, evaluates
them, and either moves on or re-spawns the agent with targeted feedback.

---

## Previewing and rendering

After `code-agent` reports `Code complete`:

```bash
python studio.py how-wifi-works-v2
```

This launcher (`studio.py` at the repo root) sets `OVG_TOPIC` and runs
`npm run studio` inside `studio/` for you on Windows, macOS, or Linux. Studio
opens at <http://localhost:3000> and loads:

- `Outputs/{TOPIC}/Video/Latest/composition.tsx` — the Remotion composition
- `Outputs/{TOPIC}/public/` — assets resolved via `staticFile()`
- `Outputs/{TOPIC}/public/audio/latest.mp3` — narration track

To render to MP4:

```bash
cd studio
OVG_TOPIC=how-wifi-works-v2 npm run render
# Windows (cmd): set OVG_TOPIC=how-wifi-works-v2 && npm run render
```

The output file lands in `studio/out/video.mp4`.

---

## Regenerating a single scene

You don't have to re-run the whole pipeline to fix one weak scene.

**Code only (direction is fine):**

1. In Claude Code, say: *"Re-spawn the code-agent for scene 3 of `how-wifi-works-v2`."*
2. The agent re-runs `cli_pipeline pre`, regenerates only `scene_3.tsx`, and re-writes the composition. Refresh Studio.

**Direction + code:**

1. Edit the scene's entry directly in `Outputs/{TOPIC}/Direction/Latest/latest.json`.
2. Ask Claude Code to re-spawn `code-agent` for that scene index.

**Direction + new assets + code:**

1. Edit the scene in `latest.json`, including any new `@asset` references and `required_assets` entries.
2. Ask Claude Code to re-spawn `asset-agent` (specify the new asset names) and then `code-agent` for the scene index.

**Full direction rewrite (last resort):**

Delete `Direction/Latest/latest.json` and ask the orchestrator to regenerate
everything. Audio and code will need to be re-run after.

---

## Project layout

```
OVG/
├── scripts/                          # Python orchestrator
│   ├── cli_pipeline.py               # the orchestrator CLI (init/pre/post/info/prompts)
│   ├── claude_cli/                   # per-step pre/post implementations
│   │   ├── content_video_direction/
│   │   ├── content_audio/
│   │   ├── asset_generator/
│   │   └── content_video/
│   ├── controllers/                  # manifest, output, metadata controllers
│   ├── server_agents/                # FastAPI server variant + agent helpers
│   └── utility/                      # ElevenLabs TTS, audio batching, config
│
├── video-tools/                      # Python tools CLI (called by sub-agents)
│   ├── scripts/
│   │   ├── tools_cli.py              # entry point: get_asset, validate_*, svg_path, ...
│   │   ├── assets/                   # icon search, company-logo lookup
│   │   ├── svg_gen/                  # math-based SVG path generator
│   │   ├── validation/               # JSON / TSX / script-with-emotions validators
│   │   └── sound_effect/             # ElevenLabs SFX generation
│   └── node_modules/                 # iconify, react-icons, simple-icons (asset sources)
│
├── prompts/                          # Prompt templates the pre-step substitutes into
│   └── orchestrator/                 # direction, audio, asset, code, script templates
│
├── studio/                           # Remotion Studio workspace for local preview
│   └── src/                          # composition entry, alias resolver
│
├── Outputs/                          # Per-topic runtime artifacts (gitignored)
│   └── {TOPIC}/
│       ├── manifest.json             # topic metadata: style, ratio, viewport, step versions
│       ├── script.md                 # final voiceover script (input to init)
│       ├── Scripts/                  # script-agent drafts + evals + emotion-tagged version
│       │   ├── drafts/script_v{N}.txt
│       │   ├── drafts/eval_v{N}.txt
│       │   ├── drafts/director_hints.txt    # optional pass-through visual hints
│       │   ├── script-user-input.md         # copy of the input init read
│       │   ├── script.md                    # narration extracted by direction post
│       │   └── script-with-emotions.md      # ElevenLabs-tag-annotated version
│       ├── Direction/
│       │   ├── Prompts/prompt.md
│       │   └── Latest/latest.json           # the scene-by-scene plan
│       ├── Audio/
│       │   ├── Prompts/prompt.md
│       │   └── latest.mp3                   # ElevenLabs TTS output
│       ├── Transcript/latest.json           # per-word frame timestamps
│       ├── Assets/
│       │   ├── Prompts/prompt.md
│       │   └── Latest/                      # SVGs/PNGs + asset_description.json
│       ├── Video/
│       │   ├── Prompts/prompt_{i}.md        # one prompt per scene
│       │   └── Latest/
│       │       ├── scene_{i}.tsx            # generated Remotion scenes
│       │       └── composition.tsx          # the composition Studio loads
│       └── public/                          # what Remotion's staticFile() serves
│           ├── *.svg | *.png                # mirrored assets
│           └── audio/latest.mp3             # mirrored narration
│
├── .claude/
│   ├── CLAUDE.md                     # the orchestrator's system prompt
│   ├── agents/                       # the five sub-agent definitions
│   │   ├── script-agent.md
│   │   ├── direction-agent.md
│   │   ├── audio-agent.md
│   │   ├── asset-agent.md
│   │   └── code-agent.md
│   └── skills/                       # reference banks the agents read on demand
│       ├── script-writer/
│       ├── video-director/           # scene examples by category, hooks, UI mockups, maps
│       └── remotion-best-practices/  # rules for fonts, transitions, mockups, maps, etc.
│
├── studio.py                         # OS-agnostic launcher: `python studio.py {TOPIC}`
├── example.env                       # template — copy to .env
├── requirements.txt                  # orchestrator deps
└── README.md                         # this file
```

---

## CLI reference

### Pipeline CLI — `python -m scripts.cli_pipeline`

Run from the OVG root.

| Subcommand | Purpose |
|---|---|
| `init --topic TOPIC --script PATH [--style STYLE] [--ratio RATIO] [--voice-id ID]` | Create `manifest.json` and copy the script into the topic folder. Run once per topic. |
| `pre --topic TOPIC --step {direction\|audio\|assets\|code}` | Build the prompt file for that step. *(Sub-agents call this themselves — you rarely need to.)* |
| `post --topic TOPIC --step {direction\|audio\|assets\|code} [--use-fallback]` | Validate, version, and finalize that step. *(Sub-agents call this themselves.)* |
| `info --topic TOPIC` | Print the parsed manifest JSON — shows style, ratio, viewport, and what's been generated. |
| `prompts --topic TOPIC --step STEP` | Print the prompt file path(s) for a step. |

### Tools CLI — `python -m scripts.tools_cli`

Run from `video-tools/`. These are what the sub-agents call under the hood;
they're available for manual use too.

```bash
python -m scripts.tools_cli get_asset                       --payload payload.json
python -m scripts.tools_cli validate_json                   --file path.json [--topic TOPIC]
python -m scripts.tools_cli validate_tsx                    --payload payload.json
python -m scripts.tools_cli validate_script_with_emotions   --file path.md --topic TOPIC
python -m scripts.tools_cli svg_path                        --equation PARABOLIC --params-json '{...}'
python -m scripts.tools_cli merge_paths                     --paths-json '["M ...","M ..."]'
python -m scripts.tools_cli generate_sound_effect           --text "..." --duration 3 --output-dir .
```

`svg_path` supports `PARABOLIC`, `CIRCULAR`, `ELLIPTICAL`, `SINE_WAVE`,
`SPIRAL`, `S_CURVE`, `LINEAR`, `ARC`, `BEZIER`, `ZIGZAG`, `BOUNCE`, `SPLINE`.

---

## Troubleshooting

- **`OUTSCAL_API_KEY not set, falling back to .env values`** — informational, safe to ignore.
- **`OVG_TOPIC is not set`** — set the env var before `npm run studio`, or use `python studio.py {TOPIC}` which sets it for you.
- **Icon search is slow on first run** — the index (`.icon_index.bin`) is built once from `@iconify/json` and cached in `video-tools/node_modules/`.
- **`@topic/...` import red squiggles in your editor** — harmless. `@topic` is a webpack alias resolved at Remotion build time from `OVG_TOPIC`; TypeScript can't resolve it statically.
- **TTS fails on the primary voice** — the audio agent retries automatically with the fallback model. You can also re-run manually: `python -m scripts.cli_pipeline post --topic {TOPIC} --step audio --use-fallback`.
- **A scene renders blank in Studio** — open `Outputs/{TOPIC}/Video/Latest/scene_{i}.tsx` and check the browser console; then ask Claude Code to re-spawn `code-agent` for that scene index.
- **Maps don't render** — set `MAPBOX_TOKENS` in `.env`. Without a token, scenes that use the `mapboxToken` prop will fail.
