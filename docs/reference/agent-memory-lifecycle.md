---
sources:
  - .claude/memory/README.md
  - .claude/memory/MEMORY.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
  - src/shared/packages/pyforge-scribe/README.md
  - CLAUDE.md
  - AGENTS.md
  - docs/how-to/configure-your-coding-agent.md
verified: 2026-09-20
---

# Agent Memory Lifecycle

This reference describes the team memory schema and the `scribe capture` promotion workflow. It is intended for Agentic Framework Builders configuring Claude Code, Gemini, or custom loops against the PyForge repository.

## Two memory layers
Agentic frameworks such as Claude Code save contextual facts to a private, operator-bound auto-memory (e.g., `~/.claude/projects/<encoded-path>/memory/`). That layer is per-user: a fact learned by one agent there is invisible to every other agent, worktree and contributor.

PyForge adds a **team** layer on top of it, not in place of it. The checked-in `.claude/memory/` index is imported into every session's context (the bare `@.claude/memory/MEMORY.md` line in `CLAUDE.md`), so anything that passes the team-relevance test in `.claude/memory/README.md` belongs there; purely personal preferences stay in auto-memory.

## The `.claude/memory/` Schema
Team-relevant architectural decisions, failure-mode traps, and reference facts are recorded in the shared team memory at `.claude/memory/`, curated by the Scribe station.

Each entry is one markdown file at `.claude/memory/<type>/<slug>.md` with YAML frontmatter (`name`, `description`, and `type` nested under `metadata:`, mirroring the live auto-memory shape). `MEMORY.md` is the one-line-per-entry index; keep it under 200 lines, pruning stale entries under git review.

### Fact Categories
- **`feedback/`**: Lessons learned from failures (e.g., "Read a detector's exit code directly, never through a pipe").
- **`project/`**: Current project state that is expected to expire (e.g., "the fleet inbox is not a second decompose wave").
- **`reference/`**: Durable facts about the environment and its tools (e.g., "the fleet landing-pass liveness check is `bmad-loop status <run_id> --json`").

## The `scribe capture` Workflow

When an agent learns a team-relevant fact or a decision is made, record it through the Scribe station rather than editing the index by hand. `scribe` runs from the `pyforge-guild` session default (scribe Story 19.2):

```bash
pixi run -e pyforge-guild scribe capture --type <feedback|project|reference> --text "Your fact here"
```

### Promoting Auto-Memory
If a useful fact is trapped in a user's local auto-memory, propose its promotion to the team layer:
```bash
pixi run -e pyforge-guild scribe capture --promote
```
This scans the user-local auto-memory, classifies each entry, and proposes team-voice promotions — proposal-then-confirm, never a silent copy. `--transcripts` does the same over raw session transcripts, and `--source <path>` overrides the auto-detected directory for either.

### Recall
`scribe recall "<question>"` answers from the compiled graph with a resolvable citation, or reports no grounded coverage — it never invents an uncited answer. `scribe graph compile` rebuilds that graph from `.claude/memory/`, the Spec memlogs, git history, retros and CHANGELOGs; with its heavy extras it runs in `-e pyforge-scribe`.

## Integration Requirements for New Agents
If you are building a new agent loop to run against PyForge:
1. Load `.claude/memory/MEMORY.md` into the agent's context at session start (Claude Code gets it through the `CLAUDE.md` import; other harnesses must read it explicitly). The rules file itself is a separate matter: `AGENTS.md` reaches Claude Code through `CLAUDE.md`'s `@AGENTS.md` import on every version, and natively on 2.1.277+ once the built-in `agents-md` mod is pinned to `claude-md-and-agents-md`; see [Configure your coding agent](../how-to/configure-your-coding-agent.md) for the per-harness setting.
2. Give the agent a shell capability that can invoke `scribe capture` for team-relevant findings, and `scribe recall` before re-deriving something the team may already know.
