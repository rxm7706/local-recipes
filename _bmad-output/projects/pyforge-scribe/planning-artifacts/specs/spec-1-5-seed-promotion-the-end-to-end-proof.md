---
title: "Story 1-5: Seed promotion — the end-to-end proof"
type: "feature"
created: "2026-08-07"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-08"
---

<!-- RECOVERED 2026-08-08 Tier 3 (epics.md-derived Intent + ACs). No session transcript or
     bmad-loop worktree snapshot survived for this story — regenerated from epics.md per
     CLAUDE.md's recovery priority order. -->

## Intent
The two existing BMAD↔CFE feedback rules are promoted as Epic 1's seed content, performed by
invoking `scribe capture --promote` itself — proving Epic 1's promotion loop against real
entries, not synthetic ones. This story closes Epic 1.

## Acceptance Criteria

- **Given** Stories 1.1-1.4 are complete, **When** `scribe capture --promote` is invoked against
  the real user-local entries `feedback_bmad_uses_cfe_skill.md` and
  `feedback_bmad_runs_cfe_retro.md`, **Then** both are classified team-relevant, proposed,
  confirmed, and written to `.claude/memory/feedback/` in team voice, `MEMORY.md` lists both with
  one-line hooks, and both source user-local entries become pointer stubs — matching the legacy
  spec's Story 6/AC-4/AC-5 exactly.
- **And** the promotion is performed by the tool, not authored by hand — the story is complete
  only when the CLI workflow itself produces the diff that gets committed (legacy spec Story 6's
  binding requirement, carried forward unchanged).

## Delivery Record
Merged via PR #296 (`scribe: Epic 1 close-out — Stories 1.4-1.5 (pointer-stub write-back, real
seed promotion)`), merge commit `75696cc29b`, 2026-08-07T16:25:58Z.
https://github.com/rxm7706/local-recipes/pull/296

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `ccecbf5f1c` (2026-08-07, "scribe: Story 1.5 — seed promotion, the real end-to-end proof (closes Epic 1)"); also `2c9e0f9180` (2026-08-07, "steward: Story 1.5 — the operator can see every credential, never a secret value"); also `b0bf0a6979` (2026-07-31, "doctor: Story 1.5 — `doctor check` CLI, --json, and the speed budget (EPIC 1 COMPLETE, 5/5"). Ledger row `1-5-seed-promotion-the-end-to-end-proof: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/memory/MEMORY.md`, `.claude/memory/feedback/bmad-runs-cfe-retro.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
