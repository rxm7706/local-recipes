---
doc_type: deferred-work-ledger
project: pyforge-scribe
date: 2026-07-31
status: promoted-verbatim
---

# pyforge-scribe — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-31 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown. Until today this project had **no tracked
ledger at all**, so its entire deferred-work record — 4 KB, 6 entries — existed
only in scratch space. Produced by the 2026-07-30/31 six-station fleet run and found
by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current.

**The one intentional edit is id assignment.** bmad-loop's damping output writes either
no id or a generic `DW-<n>`, which collides the moment another story is damped. Each
entry here is keyed `DW-<story>-<n>` from its own `source_spec`, per the convention the
sibling ledgers and the detector both use.

---

### DW-1-2-1

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: `.claude/memory/MEMORY.md`'s own header documents a 200-line cap ("Claude Code truncates context past that length") but nothing enforces it in CI.
  evidence: Edge Case Hunter review of Story 1.2's `CLAUDE.md` wiring diff flagged that once the `@.claude/memory/MEMORY.md` import is live, silent truncation past 200 lines would drop later-appended team-memory entries from every session with no automated warning. Out of scope for Story 1.2 (which only wires the import) and Story 1.1 (which scaffolded the file) — no CI check currently exists anywhere in the repo for this file's line count.
  status: open

### DW-1-2-2

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: In bmad-loop worktree sessions the team-memory index loads twice — once via the loop-home's ancestor `CLAUDE.md` and once via the worktree's — from two physical `.claude/memory/MEMORY.md` files that can diverge (home on `main`, worktree on a story branch).
  evidence: Observed live in the Story 1.2 review-pass-2 session: both `/home/rxm7706/.bmad-loops/pyforge-scribe/CLAUDE.md` and the run-worktree `CLAUDE.md` were in context simultaneously (Claude Code loads ancestor-directory CLAUDE.md files), each resolving the relative import against its own tree. Once this change is on `main` and pulled by the 8 loop homes, every worktree session pays the index twice. Not fixable inside Story 1.2 (imports cannot be conditional); an inherent cost of the loop-home layout that should be recorded/accepted or mitigated at the bmad-loop level.
  status: open

### DW-1-2-3

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: bmad-loop leaves an untracked, un-gitignored `claude_hash.txt` (the story's HEAD commit hash) at the run-worktree root with no identifiable in-repo producer; any later `git add -A` automation would sweep it into a commit.
  evidence: Blind Hunter verified during Story 1.2 review pass 2: the file exists at the worktree root containing exactly `0671914e15e78cc45fdb98867a64ac49f3485f5f`, `git check-ignore` reports NOT IGNORED, and `grep -rn claude_hash` across repo scripts, hooks, `.bmad-loop/`, and settings finds no generator or consumer. Loop-machinery hygiene, not Story 1.2 content — fix belongs in bmad-loop (gitignore it or write it outside the worktree).
  status: open

### DW-1-2-4

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: Nothing asserts the `@.claude/memory/MEMORY.md` import in root `CLAUDE.md` still exists and resolves — Claude Code silently ignores broken imports, so a rename/move of the memory index (or deletion of the import line) severs team memory with no failure signal anywhere.
  evidence: Story 1.2 review pass 2 confirmed no test, detector, or hook references the import (`scripts/bmad_drift_check.py` `check_coverage` walks only the `_bmad-output` project tree; no meta test greps `CLAUDE.md` for the line). Complements the already-ledgered 200-line-cap entry (different failure mode: severance vs truncation); a one-line check in an existing detector or meta-test would close both.
  status: open

### DW-1-2-5

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: Team memory is wired for Claude Code only — `AGENTS.md`, `.cursor/rules/`, `GEMINI.md`, and `.github/copilot-instructions.md` carry no pointer to `.claude/memory/MEMORY.md`, while `.claude/memory/README.md` claims the layer is loaded "into every session" for every agent.
  evidence: Verified in Story 1.2 review pass 2: grep across the cross-tool entry files finds no team-memory reference, and no story in `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md` (Epics 1–2, Stories 1.1–2.4) covers cross-tool exposure — the gap is real and unplanned, not merely sequenced later. `@import` is Claude-Code-specific syntax, so non-Claude agents never see the index.
  status: open

### DW-1-2-6

- source_spec: `_bmad-output/projects/pyforge-scribe/implementation-artifacts/spec-1-2-claude-md-wiring-team-memory-loads-automatically.md`
  summary: A future `MEMORY.md` entry containing a bare `@`-token (npm scope, GitHub handle) would be treated as a nested import attempt by Claude Code, since imports recurse into imported files — the scribe writer/README needs a backtick-all-`@`-tokens authoring rule.
  evidence: Raised by Edge Case Hunter in Story 1.2 review pass 2. Claude Code evaluates `@path` references recursively in imported files but not inside code spans; team-memory entries about npm packages plausibly contain `@scope/pkg` tokens. Guard belongs in `.claude/memory/README.md`'s entry schema and/or Story 1.3's `scribe capture` writer (backtick or escape `@`-tokens on write), both outside Story 1.2's edit-only-`CLAUDE.md` boundary.
  status: open
