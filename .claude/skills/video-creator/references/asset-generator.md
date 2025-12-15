## 1. Pre-Processing

Extract required_assets from Direction output:
```bash
python scripts/claude_cli/asset_generator/pre_process.py --topic "{topic}"
```

## 2. LLM Generation

Invoke the asset_generator agent using the Task tool:

```
Task: asset_generator agent with --topic "{topic}"
```

## 3. Post-Processing

Version SVG assets and manifest:
```bash
python scripts/claude_cli/asset_generator/post_process.py --topic "{topic}"
```
