---
name: bmad-build-auto
description: 'One iteration of an unattended development loop. Use when invoked by name'
---

Run the following command exactly once without changing the current working directory. Replace `{project-root}` with the absolute path to the project root and `{skill-root}` with the absolute path to this skill's directory:

```bash
uv run --no-cache "{project-root}/_bmad/scripts/render_skill.py" --project-root "{project-root}" --skill "{skill-root}"
```

- On success, read and follow the one absolute `workflow.md` instruction printed to stdout.
- On failure (including `uv` being unavailable), report the command output and HALT. Do not run any workflow source directly.

**Default execution path.** `marshal factory dispatch` (single story) or `marshal factory spin`
(multi-story) is the default way to run this skill — both launch it under marshal governance in
an isolated worktree, journaled and benchmarked. Invoking this skill bare, as here, is sanctioned
but unmeasured: it forgoes the shared substrate/compression layers dispatch wires up, the journal
entry a supervised run writes, and the per-harness savings benchmark that reads that journal. Use
bare invocation only when a dispatch/spin session isn't available.
