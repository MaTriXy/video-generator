<p align="center">
  <h1 align="center">Outscal Video Generator</h1>
  <p align="center">An AI-powered video generation tool that creates animated videos from text scripts using Claude Code.</p>
  <p align="center">
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Mac%20%7C%20Linux-blue" alt="Platform"/>
    <img src="https://img.shields.io/badge/python-3.13+-blue" alt="Python"/>
    <img src="https://img.shields.io/badge/built%20with-Claude%20Code-orange" alt="Built with Claude Code"/>
    <img src="https://img.shields.io/badge/built%20with-React-61DAFB?logo=react" alt="Built with React"/>
    <img src="https://img.shields.io/badge/TTS-ElevenLabs-black" alt="TTS"/>
  </p>
</p>

## 📑 Table of Contents

- [How It Works](#-how-it-works)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Video Creation Workflow](#-video-creation-workflow)
- [Video Art Styles](#-video-art-styles)
- [Commands Reference](#-commands-reference-fyi)

## 💡 How It Works

Unlike traditional AI video generators that output video files, this tool generates **React/TSX code** that renders as animated videos. The AI writes the code—the code becomes the video.

## 📋 Prerequisites

- **Claude Code CLI** installed and configured. see [Claude Code Quickstart](https://code.claude.com/docs/en/quickstart)

## 🚀 Quick Start

> **⚡ TL;DR:** Clone repo → Run `/tools:init` → Set API key → Run `/create-video`

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

> [!NOTE]
> This command only needs to be run once during initial setup.

### 3. API Key Setup (Required)

After installation completes, you need to set up your API key (this will be instructed after the `/tools:init` comand as well):

1. **Get your API key**: Visit [https://production2.outscal.com/v2/get-video-generation-api-key](https://production2.outscal.com/v2/get-video-generation-api-key) and register or login
2. **Add your API key** to the `.env` file:
   ```
   OUTSCAL_API_KEY="your_api_key_here"
   ```
   Replace `your_api_key_here` with the actual API key you received.

### 4. Optional Environment Variables

The following environment variable is **optional** and only needed if you want to use a different voice:

| Variable | Description | Required |
|----------|-------------|----------|
| `ELEVENLABS_VOICE_ID` | Voice ID from ElevenLabs. You can pick different voice IDs from your ElevenLabs account if you want to change the voice. | No |

> [!NOTE]
> Only ElevenLabs' pre-made voices are supported. Custom or cloned voices will not work.

### 5. Create Your Video

Run the video creation command:

```
/create-video
```

> [!TIP]
> Run this command every time you want to create a new video.

## 🔄 Video Creation Workflow

When you run `/create-video`, the tool will guide you through this pipeline:

```
┌─────────┐   ┌─────────┐   ┌───────────┐   ┌───────────┐   ┌────────┐   ┌────────┐   ┌───────┐
│  Style  │ → │ Script  │ → │   Audio   │ → │ Direction │ → │ Assets │ → │ Design │ → │ Video │
└─────────┘   └─────────┘   └───────────┘   └───────────┘   └────────┘   └────────┘   └───────┘
```

| Step | What Happens |
|------|--------------|
| 🎨 **Style** | Choose from available art styles |
| 📝 **Script** | Provide your narration script (max 2000 characters) |
| 🔊 **Audio** | Convert script to speech using ElevenLabs |
| 🎬 **Direction** | Generate scene-by-scene video direction |
| 🖼️ **Assets** | Create SVG assets for the video |
| ✏️ **Design** | Generate detailed design specifications |
| 🎥 **Video** | Create and deploy video (displays deployed URL) |

> [!TIP]
> After videos are created and deployed, use `/tools:list-videos` to view all deployed video URLs.

## 🎨 Video Art Styles
When creating a video, you'll be asked to choose from three distinct visual styles:

### Pencil
https://github.com/user-attachments/assets/318eb537-d152-4816-b948-ff3d695e1ed0

A hand-drawn, sketch-like aesthetic that gives videos a personal, artistic feel. Features rough edges, sketch lines, and a notebook-paper appearance. Great for educational content that wants to feel approachable and informal.

### Infographic
https://github.com/user-attachments/assets/500a103b-1856-4882-9002-099234d274a3

Clean, modern, and professional style with bold colors, geometric shapes, and data visualization elements. Uses flat design principles with clear iconography. Ideal for business presentations, explainer videos, and data-driven content.

### Neon
https://github.com/user-attachments/assets/8c57e9cf-47cf-46e1-a0f1-8fa3d5da016b

Vibrant, futuristic style with glowing effects, dark backgrounds, and bright accent colors. Features electric highlights and cyberpunk-inspired visuals. Perfect for tech topics, gaming content, or when you want a high-energy, modern look.

## 📖 Commands Reference (FYI)

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

> [!IMPORTANT]
> If you run individual `gen:` commands instead of `/create-video`, you must run all subsequent commands in the workflow sequence for your changes to take effect. For example, if you run `/gen:director`, you'll need to manually run `/gen:assets`, `/gen:design`, and `/gen:video` afterwards.

