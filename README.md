# Video Generator

An AI-powered video generation tool that creates animated educational videos from text scripts using Claude Code.

## Prerequisites

- **Claude Code CLI** installed and configured

## Quick Start

### 1. Environment Setup

Copy the `.env.template` file to create your `.env` file:

```bash
cp .env.template .env
```

Edit the `.env` file and fill in your API keys:

| Variable | Description |
|----------|-------------|
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key for observability |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key for observability |
| `PAYLOAD_AUTH_TOKEN` | Payload CMS authentication token |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for text-to-speech |
| `ELEVENLABS_VOICE_ID` | Voice ID to use for narration |
| `ELEVENLABS_MODEL_ID` | ElevenLabs model ID |
| `ELEVENLABS_SPEED` | Speech speed setting |
| `ELEVENLABS_STABILITY` | Voice stability setting |
| `ELEVENLABS_SIMILARITY` | Voice similarity setting |
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 storage |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 storage |

### 2. Install Dependencies

Run the initialization command in Claude Code:

```
/tools:init
```

This will automatically:
- Install Python 3.13 if not already installed
- Install all pip packages from `requirements.txt`
- Run `npm install` in the visualise_video directory

### 3. Create Your Video

Run the video creation command:

```
/create-video
```

## Video Creation Workflow

When you run `/create-video`, the tool will:

1. **Ask for Video Style** - Choose from available art styles
2. **Ask for Script** - Provide your narration script (max 2000 characters)
3. **Generate Audio** - Convert script to speech using ElevenLabs
4. **Create Direction** - Generate scene-by-scene video direction
5. **Generate Assets** - Create SVG assets for the video
6. **Design Scenes** - Generate detailed design specifications
7. **Video** - Create Video


## Video Art Styles

When creating a video, you'll be asked to choose from three distinct visual styles:

### Pencil
A hand-drawn, sketch-like aesthetic that gives videos a personal, artistic feel. Features rough edges, sketch lines, and a notebook-paper appearance. Great for educational content that wants to feel approachable and informal.

### Infographic
Clean, modern, and professional style with bold colors, geometric shapes, and data visualization elements. Uses flat design principles with clear iconography. Ideal for business presentations, explainer videos, and data-driven content.

### Neon
Vibrant, futuristic style with glowing effects, dark backgrounds, and bright accent colors. Features electric highlights and cyberpunk-inspired visuals. Perfect for tech topics, gaming content, or when you want a high-energy, modern look.

## Commands Reference

| Command | Description |
|---------|-------------|
| `/create-video` | Start the full video creation workflow |
| `/tools:init` | Install all project dependencies |
| `/gen:audio --topic "topic-name"` | Generate audio only |
| `/gen:director --topic "topic-name"` | Generate video direction only |
| `/gen:assets --topic "topic-name"` | Generate SVG assets only |
| `/gen:design --topic "topic-name"` | Generate design specifications only |
| `/gen:video --topic "topic-name"` | Generate video components only |

## Project Structure

```
video-generator/
├── .claude/
│   ├── commands/          # Claude Code slash commands
│   └── skills/            # Claude Code skills
├── scripts/
│   ├── init/              # Installation scripts
│   ├── claude_cli/        # CLI workflow scripts
│   └── utility/           # Utility scripts (TTS, etc.)
├── visualise_video/       # React video rendering app
└── Outputs/               # Generated video outputs
```