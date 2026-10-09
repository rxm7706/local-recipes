# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The cross-tool contract lives in `AGENTS.md` (the verified `bmad:context` block, the team-memory
boot line, the pre-PR checklist); with a `CLAUDE.md` present, Claude Code reads it only through the
import below — keep this line bare (`spec-pyforge-scribe` CAP-27).

@AGENTS.md

## Interactive session path

`marshal factory dispatch` / `spin` are the **measured** path (policy-rendered, journaled,
benchmarked). An interactive Claude Code session on the shared checkout is the **documented
convenience path** — the same instruments, wired by hand, from repo root:

```bash
caveman-install --only claude --with-hooks   # once per machine: output-compression skill + hooks
headroom wrap claude --code-memory none      # launch this session behind the wire-compression proxy
```

Neither path gets a second kit, and the interactive path gets no separate benchmark (operator
decision 2026-09-16; `spec-pyforge-marshal` CAP-195, folded from `spec-marshal-token-economy`
CAP-22). Once the session is open, retrieve/recall discipline replaces wholesale `epics.md` /
PRD loads — see AGENTS.md § *Scribe recall (session path)* and `marshal context retrieve`.

**Behavioural guidelines** — the eight principles every harness follows (Think before coding · Simplicity first · Surgical changes, healed tissue · Goal-driven execution · Dream to code, always · State over action · Harness-owned ledgers are read-only · Implementation and review stay separate) live in `AGENTS.md` § *Behavioural guidelines (every harness)*, imported above; the `conda-forge-expert` skill specialises them for recipe work and the BMAD skills for planning/dev. Not restated here (scribe CAP-27, point-don't-copy; CAP-29 collapsed the duplicate).

## Legacy intake-spec index (read by `bmad-drift-check`)

Doctor's `bmad-drift-check` detector (`check_spec_indexed`) requires every `docs/specs/*.md` filename
to appear in this file. Author no new file there (`AGENTS.md` § *The tiers*); descriptions and
the shipped rows: `docs/reference/agent-instruction-notes.md` § *Intake specs*.

| Spec | Status |
|---|---|
| `docs/specs/flyte-conda-forge.md` | in-progress |
| `docs/specs/feedstock-refresh.md` | in-progress |
| `docs/specs/feedstock-platform-expansion.md` | workflow stub; body in `.claude/skills/mason-feedstock-platform-expansion/` |
| `docs/specs/feedstock-failure-remediation.md` | workflow stub; body in `.claude/skills/mason-feedstock-failure-remediation/` |
| `docs/specs/presentation-deck.md` | workflow stub; body in `docs/how-to/presentation-deck.md` |

## Where moved sections went

This file carried more sections until 2026-09-26 (scribe Story 21.1). A link that names one
lands here: where each went, and its full former text, are in
`docs/reference/agent-instruction-notes.md` § *Moved from CLAUDE.md*.

### Spec-driven, framework-neutral layout

Now `AGENTS.md` § *The tiers* (including the durable story-spec rule) and § *Dream-first workflow*.

### Multi-Project Pattern

The rules, including PARALLEL AGENTS: `AGENTS.md` § *Policy* and § *Dream-first workflow* item 6.
Config layers: `_bmad-output/PROJECTS.md`; the marker-and-symlink mechanism: the notes file
§ *Multi-Project Pattern*.

## Team Memory

This repo carries a checked-in team-memory index at `.claude/memory/MEMORY.md` — one-line entries capturing team-relevant decisions, feedback, and reference material as reviewable prose (see `.claude/memory/README.md` for the schema and promotion workflow). It is imported below so the index is in context for every session. The import line must stay bare — a backticked `@path` is an inert code span, not an import.

The session-close ritual is `scribe capture`, stated once, in `AGENTS.md` § *Team memory — read at
session start, every harness* (imported above via `@AGENTS.md`) — not restated here.

@.claude/memory/MEMORY.md
