# OVG — Outscal Video Generator

> **Getting started?** Ask your coding agent (Claude Code) to read this
> `README.md` end-to-end and set up the project for you. It will install the
> Python and Node dependencies, guide you through filling in `.env`, and
> verify the pipeline is ready to run.

A Claude-Code-driven pipeline that turns a plain-text script into an animated
Remotion video you can preview locally. The four steps — direction, audio,
assets, code — are each handled by a specialized sub-agent coordinated from
your Claude Code session.

## Prerequisites

- **Python 3.13**
- **Node.js 18+** (for the Remotion Studio preview and the iconify asset index)
- **Claude Code** installed and authenticated
- **API keys** — at minimum an Anthropic Claude Code OAuth token and an
  ElevenLabs key. See [`example.env`](./example.env) for the full list.

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

# 4. Node deps for the iconify icon library
cd video-tools && npm install && cd ..

# 5. Node deps for the Remotion Studio preview
cd studio && npm install && cd ..
```

## Project layout

```
OVG/
├── scripts/             # Python orchestrator — pipeline steps + claude-cli glue
├── video-tools/         # Python tools CLI (validate, get_asset, svg_path, TTS, SFX)
│   └── node_modules/    # Iconify & react-icons — source of all icon assets
├── prompts/             # Per-step prompt templates (direction, scene, etc.)
├── studio/              # Remotion Studio workspace for local preview
├── Outputs/             # Per-topic runtime artifacts (gitignored)
│   └── {TOPIC}/
│       ├── script.md                       # your input
│       ├── manifest.json
│       ├── Direction/Latest/latest.json
│       ├── Audio/latest.mp3
│       ├── Transcript/latest.json
│       ├── Assets/Latest/*.svg
│       ├── Video/Latest/scene_{i}.tsx      # generated scenes
│       ├── Video/Latest/composition.tsx    # Remotion composition
│       └── public/                         # what Studio serves via staticFile()
├── .claude/             # Orchestrator instructions + agent definitions
├── .env                 # your secrets (gitignored)
└── example.env          # template
```

## Generating a video

The pipeline is driven by Claude Code. Open the project in Claude Code
(`claude` from the OVG root) and ask the main chat to generate a video —
it reads `.claude/CLAUDE.md` and knows what to do.

### 1. Write a script

Save your narration script to `Outputs/{TOPIC}/script.md`, where `{TOPIC}` is
a slug ending in `-v2` (e.g. `how-wifi-works-v2`). One paragraph per scene
works best, but any prose is fine — the direction step will break it up.

### 2. Initialize the topic

```bash
python -m scripts.cli_pipeline init \
  --topic how-wifi-works-v2 \
  --script Outputs/how-wifi-works-v2/script.md \
  --style vox \
  --ratio 9:16
```

- `--style` — `4g5g | brutalism | glitch-art | memphis | neobrutalism | risograph | synthwave | typography-apple | vox`
- `--ratio` — `9:16` (portrait) or `16:9` (landscape)
- `--voice-id` — optional ElevenLabs voice override

### 3. Let the orchestrator run the four steps

In the Claude Code chat at the OVG root, say something like:

> Generate the video for `how-wifi-works-v2`.

The orchestrator will spawn each sub-agent in order:

| Step | Sub-agent | What it produces |
|------|-----------|------------------|
| 1. Direction | `direction-agent` | Scene-by-scene visual plan in `Direction/Latest/latest.json` |
| 2. Audio     | `audio-agent`     | `Audio/latest.mp3` + per-scene frame timestamps |
| 3. Assets    | `asset-agent`     | SVGs in `Assets/Latest/` mirrored into `public/` |
| 4. Code      | `code-agent`      | `Video/Latest/scene_{i}.tsx` + `composition.tsx` |

Each sub-agent runs its own pre-processing and post-processing internally.
The orchestrator reviews each step's output against the quality bar and can
loop back to rework weak scenes.

### 4. Preview in Remotion Studio

After the code-agent reports `Code complete`:

```bash
cd studio
OVG_TOPIC=how-wifi-works-v2 npm run studio
# Windows: set OVG_TOPIC=how-wifi-works-v2 && npm run studio
```

Studio opens on <http://localhost:3000> and loads
`Outputs/{TOPIC}/Video/Latest/composition.tsx`, using `Outputs/{TOPIC}/public/`
as the asset root and `public/audio/latest.mp3` as the narration track.

To render the preview to an `.mp4`:

```bash
OVG_TOPIC=how-wifi-works-v2 npm run render
```

The output file lands in `studio/out/video.mp4`.

## Regenerating a single scene

You don't have to re-run the whole pipeline to fix one weak scene.

1. Edit the scene's entry in `Outputs/{TOPIC}/Direction/Latest/latest.json`.
2. In Claude Code, say: _"Re-spawn the code-agent for scene 3."_ The agent
   re-runs `cli_pipeline pre`, regenerates only that scene's `scene_3.tsx`,
   and re-writes the composition. Refresh Studio to see the new scene.

For scene-level re-generation that also needs new assets, re-spawn the
`asset-agent` first with the new asset names, then the `code-agent`.

## Manifest state

```bash
python -m scripts.cli_pipeline info --topic {TOPIC}
```

Prints the parsed manifest JSON — shows which steps have run, their versions,
and the current metadata (viewport, voice, style).

## Useful tools_cli subcommands

Run from `video-tools/`:

```bash
python -m scripts.tools_cli get_asset              --payload payload.json
python -m scripts.tools_cli validate_json          --file path.json
python -m scripts.tools_cli validate_tsx           --payload payload.json
python -m scripts.tools_cli svg_path               --equation PARABOLIC --params-json '{...}'
python -m scripts.tools_cli generate_sound_effect  --text "..." --duration 3 --output-dir .
```

These are what the sub-agents invoke under the hood; they're available for
manual use too.

## Troubleshooting

- **`OUTSCAL_API_KEY not set, falling back to .env values`** — informational,
  safe to ignore.
- **`OVG_TOPIC is not set`** — set the env var before `npm run studio`.
- **Icon search is slow on first run** — the index (`.icon_index.bin`) is
  built once from `@iconify/json` and cached in `video-tools/node_modules/`.
- **`@topic/...` import red squiggles in editor** — harmless. `@topic` is a
  webpack alias resolved at Remotion build time from `OVG_TOPIC`; TypeScript
  can't resolve it statically.
