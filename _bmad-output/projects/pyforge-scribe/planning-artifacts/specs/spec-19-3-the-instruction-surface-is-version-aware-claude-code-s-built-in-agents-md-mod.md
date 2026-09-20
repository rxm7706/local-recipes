---
title: '19.3: The instruction surface is version-aware — Claude Code''s built-in agents-md mod'
type: 'feature'
created: '2026-09-20'
status: 'done'
baseline_revision: '08c466b8256359386772797845a4f3cd9408b2ed'
final_revision: 'pending — the merge commit of the fleet/agents-md-mod PR'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-scribe/planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md'
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Claude Code 2.1.277 (2026-09-18) ships a built-in `agents-md` mod. Its default mode stays out of any project that has a `CLAUDE.md`, so in this repo the mod does nothing and `AGENTS.md` still reaches Claude Code only through `CLAUDE.md`'s bare `@AGENTS.md` import — while the atlas child `src/shared/packages/pyforge-atlas/AGENTS.md` never reaches it at all. The harness table said "only through that import" unconditionally; `CLAUDE.md` and `AGENTS.md` both carried the five guidelines under differently-spelled H2s the parity guard could not see; nothing told an operator their runtime or mode was behind.

**Approach:** keep the import as the floor; state version and pinned mode in the harness table; pin `instructionFiles: claude-md-and-agents-md` in the operator's user settings (the dispatch launch is marshal's, Story 46.11); collapse the duplicate to a pointer and make the parity guard compare normalised headings; repoint `.claude/settings.json`'s `customInstructions` at `AGENTS.md`; add a runtime-scope currency check; document per harness through the Diátaxis skill.

## Boundaries & Constraints

**Always:**
- The `@AGENTS.md` import stays bare and present — nothing depends on the mod being installed
- The check is advisory (warn), runtime scope, silent without a `claude` binary, never in `detectors-ci`
- Per-tool files carry no section `AGENTS.md` carries, compared after spelling normalisation

**Never:**
- Do not delete `CLAUDE.md` to "default to `AGENTS.md`" — it is the import vehicle for older / enterprise runtimes and carries Claude-only addenda
- Do not put the mode in the project's `.claude/settings.json` — the mod does not read it there

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| this host | Claude Code 2.1.278, mode pinned | check prints ok, exit 0 | n/a |
| mode unpinned | user settings without the option | check warns naming the setting, exit 1 | advisory |
| old runtime | `claude --version` < 2.1.277 | check warns "predates the mod", exit 1 | advisory |
| no claude | binary absent | silent, exit 0 | n/a |
| duplicate H2 | `## Behavioral Guidelines` in a per-tool file | parity guard reds it (normalised) | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-29`.
Surface: `AGENTS.md` (Claude Code row), `CLAUDE.md` (guidelines collapsed to a pointer), `.claude/settings.json` (`customInstructions`), `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py`, `scripts/claude_instruction_mode_check.py`, `pixi.toml` (`claude-instruction-mode-check`), `docs/how-to/configure-your-coding-agent.md` (new, via `bmad-os-diataxis`), `docs/reference/agent-memory-lifecycle.md`, `docs/MAP.md`, `planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md` (§ 7 addendum).
Ledger key: `19-3-the-instruction-surface-is-version-aware-claude-code-s-built-in-agents-md-mod`.
Hand-driven 2026-09-20 in the fleet PR with marshal 46.11.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild claude-instruction-mode-check` on this host → ok; `docs-map-hygiene` green after the how-to lands.

## Review Triage Log

### 2026-09-20 — hand-driven pass
  - `[medium]` `[patch]` the harness table's Claude Code row was unconditional ("only through that import") — true only below 2.1.277 / default mode. Rewritten with version, mode, nested-file behaviour and the floor.
  - `[low]` `[patch]` `CLAUDE.md` "Behavioral Guidelines" duplicated `AGENTS.md` "Behavioural guidelines (every harness)" under a spelling the casefold guard could not match. Collapsed to a pointer; guard normalises spelling and parentheticals.
  - `[low]` `[patch]` `.claude/settings.json` `customInstructions` cited `CLAUDE.md` for the guidelines. Repointed.
  - `[low]` `[reject]` make the check a doctor source — it reads host state (binary + user settings), which is runtime scope by the registry's own rule; a `scripts/*_check.py` with `DETECTOR = {"scope": "runtime"}` and a pixi task is the sanctioned shape (`loop-stall-check` precedent).

## Auto Run Result

**Status:** done
**Summary:** the surface is version-aware: import floor kept, mode pinned (operator settings written on this host; dispatch launch pinned by 46.11), harness table current, duplicate collapsed with a normalising guard, currency check registered, and the docs refreshed through `bmad-os-diataxis` (new how-to + reference update + MAP row).
**Verification:** `test_instruction_surface_parity.py` 23 passed (5 new); `claude-instruction-mode-check` ok on this host, exit 2 with a bogus binary; `docs-map-hygiene` ok; `pyforge-scribe-test` — see the PR body for the count.
**Files changed:** see Binding.
**Residual risks:** the mode lives in user settings, so a new machine reads unpinned until the operator runs the check and sets it (the how-to says how); dispatched sessions are unaffected.
**Follow-up review recommendation:** false
