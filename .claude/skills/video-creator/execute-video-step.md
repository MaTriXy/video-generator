# Execute Video Step

Execute a single video step for an existing topic.

## Workflow

**Step 0: Get Topic (if not provided)**

If the user has not provided a topic name, ask them to specify which topic they want to work with.

**Step 1: Identify the requested step**

From the user's request, identify which step to run:
- `audio` → Audio generation
- `direction` → Video direction creation
- `assets` → SVG asset generation
- `design` → Design specification generation
- `code` → Video component coding 

**Step 2: Execute the step**

Read and execute the corresponding step file.

