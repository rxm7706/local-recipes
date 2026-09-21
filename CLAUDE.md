# CLAUDE.md

Claude Code loads the shared contract through the import below. Do not fork
policy here (`AGENTS.md` is the single instruction surface).

@AGENTS.md

## Claude-only session notes

* Prefer `bmad-loop` / measured marshal dispatch when the operator wants a
  journaled run; an interactive session is the convenience path, not a second
  kit.
* At session start: read `.claude/memory/MEMORY.md`, then confirm A vs B and the
  active BMAD project before writing artifacts.
* Recipe work: load `conda-forge-expert` (or successor) on demand — do not keep
  full recipe doctrine in this file.
