# Video Generator

An AI-powered video generation tool that creates animated educational videos from text scripts using Claude Code.

## Prerequisites

- **Claude Code CLI** installed and configured. see [Claude Code Quickstart](https://code.claude.com/docs/en/quickstart)

## Quick Start

### 1. Clone and Setup

1. **Get the repository**: Either clone the repository or download it as a ZIP file and extract it.
   
2. **Open Claude Code** in the repository directory to ensure all commands work properly.

### 2. Install Dependencies

Run the initialization command in Claude Code:

```
/tools:init
```

This command will automatically:

- install the requirements needed to start generating video
- will direct you to setup the api key and will tell you how.

**Note:** This command only needs to be run once during initial setup.

### 3. API Key Setup (Required)

After installation completes, you need to set up your API key (this will be instructed after the `/tools:init` comand as well):

1. **Get your API key**: Visit [https://production2.outscal.com/v2/get-video-generation-api-key](https://production2.outscal.com/v2/get-video-generation-api-key)
2. **Register or login** to get your API key
3. **Create a `.env` file** in the project root directory (if it doesn't exist)
4. **Add your API key** to the `.env` file:
   ```
   OUTSCAL_API_KEY="your_api_key_here"
   ```
   Replace `your_api_key_here` with the actual API key you received.

### 4. Optional Environment Variables

The following environment variable is **optional** and only needed if you want to use a custom voice:

| Variable | Description | Required |
|----------|-------------|----------|
| `ELEVENLABS_VOICE_ID` | Voice ID from ElevenLabs. You can pick different voice IDs from your ElevenLabs account if you want to change the voice. | No |

### 5. Create Your Video

Run the video creation command:

```
/create-video
```

**Note:** Run this command every time you want to create a new video.

## Video Creation Workflow

When you run `/create-video`, the tool will:

1. **Ask for Video Style** - Choose from available art styles
2. **Ask for Script** - Provide your narration script (max 2000 characters)
3. **Generate Audio** - Convert script to speech using ElevenLabs
4. **Create Direction** - Generate scene-by-scene video direction
5. **Generate Assets** - Create SVG assets for the video
6. **Design Scenes** - Generate detailed design specifications
7. **Video** - Create and deploy video (displays deployed URL)

**Tip:** After videos are created and deployed, use `/tools:list-videos` to view all deployed video URLs.

## Video Art Styles
When creating a video, you'll be asked to choose from three distinct visual styles:

### Pencil
A hand-drawn, sketch-like aesthetic that gives videos a personal, artistic feel. Features rough edges, sketch lines, and a notebook-paper appearance. Great for educational content that wants to feel approachable and informal.

### Infographic
Clean, modern, and professional style with bold colors, geometric shapes, and data visualization elements. Uses flat design principles with clear iconography. Ideal for business presentations, explainer videos, and data-driven content.

### Neon
Vibrant, futuristic style with glowing effects, dark backgrounds, and bright accent colors. Features electric highlights and cyberpunk-inspired visuals. Perfect for tech topics, gaming content, or when you want a high-energy, modern look.

## Commands Reference (FYI)

| Command | Description |
|---------|-------------|
| `/tools:init` | Install all project dependencies |
| `/tools:list-videos` | List all deployed video URLs for the project |
| `/create-video` | Start the full video creation workflow |
| `/gen:audio --topic "topic-name"` | Generate audio only |
| `/gen:director --topic "topic-name"` | Generate video direction only |
| `/gen:assets --topic "topic-name"` | Generate SVG assets only |
| `/gen:design --topic "topic-name"` | Generate design specifications only |
| `/gen:video --topic "topic-name"` | Generate video components only |

**Important:** If you run individual `gen:` commands instead of `/create-video`, you must run all subsequent commands in the workflow sequence for your changes to take effect. For example, if you run `/gen:director`, you'll need to manually run `/gen:assets`, `/gen:design`, and `/gen:video` afterwards.

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
