# Execute Regenerate Scenes Step

Regenerate specific scenes for a video step.

## Workflow

**Step 0: Get Topic (if not provided)**

If the user has not provided a topic name, ask them to specify which topic they want to work with.

**Step 1: Parse scenes parameter**

Extract the scene indices from the user's request. The scenes parameter should be a list of integers (e.g., [0, 2, 3]).

**Step 2: Identify the requested step**

From the user's request, identify which step to regenerate:
- `design` → Design specification regeneration
- `code` → Video component coding regeneration

**Step 3: Execute the regeneration step**

Read and execute the corresponding regenerate step file.
