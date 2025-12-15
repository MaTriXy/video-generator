---
description: generate SVG assets from Direction requirements by following the instructions given below.
allowed-tools: Task, SlashCommand
model: sonnet
argument-hint: --topic "topic-name"
---

# Asset Generation Workflow

Generate SVG assets using the three-part workflow that separates deterministic operations from LLM generation.

## Implementation Steps

Step 1: **Execute Pre-Processing**
   - Run the command below to extract required_assets from Direction and generate prompt
   ```bash
   python scripts/claude_cli/asset_generator/pre_process.py --topic "{topic}"
   ```

Step 2: **Execute Asset Generator Agent**
   - Use the Task tool to invoke the asset_generator sub-agent with --topic "{topic}"

Step 3: **Execute Post-Processing**
   - Run the command to version SVG assets and generate manifest
   ```bash
   python scripts/claude_cli/asset_generator/post_process.py --topic "{topic}"
   ```

## Error Handling
- If pre-processing fails: Display error indicating Direction must be generated first
- If asset generation fails: Display error and abort workflow
- If post-processing fails: Display error but keep generated SVGs for debugging
