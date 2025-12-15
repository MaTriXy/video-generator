# Spline Path

**Use Case:** Smooth curve through N points

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `points` | Array of [x,y] coordinates |

## Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `tension` | Curve smoothness (0-1) | 0.3 |

## Example - River flowing through landscape

```bash
python ".claude/skills/asset-creator/scripts/svg-path.py" spline --params '{"points": [[100,300], [200,100], [300,350], [400,150], [500,300], [600,100], [700,250]], "tension": 0.3}'
```
