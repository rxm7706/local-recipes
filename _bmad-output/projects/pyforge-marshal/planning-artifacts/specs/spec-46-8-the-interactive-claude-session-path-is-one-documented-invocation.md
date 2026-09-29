---
title: '46.8: The interactive Claude session path is one documented invocation'
type: 'docs'
created: '2026-09-18'
status: 'done'
baseline_revision: '4d165707d911008c7c9668dea3ad9653688cc797'
final_revision: 'dbdb0773b1'
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As an operator starting an interactive Claude session on the shared checkout, I want the wrap + caveman skill + retrieve/recall discipline written once where a session actually starts, So that the convenience path runs on the same instruments as dispatch instead of re-discovering the repo.

**Approach:** the Claude-facing session docs (CLAUDE.md session-path note) naming the one invocation; dispatch remains the measured path.

Ledger key: `46-8-the-interactive-claude-session-path-is-one-documented-invocation`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: docs / S / S-46.7.

### Living CAP citations

- `spec-pyforge-marshal` CAP-195 (fold remint of `spec-marshal-token-economy` CAP-22; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-195` ← `spec-marshal-token-economy CAP-22`.

## Acceptance Criteria

- Given an operator starts interactive Claude on the shared checkout When they follow the documented path Then the session is demonstrably wrapped or seeded per the declared `[context]` layers, and wholesale `epics.md` / PRD loads are a miss against retrieve/recall

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| an operator starts interactive Claude on the shared checkout | they follow the documented path | the session is demonstrably wrapped or seeded per the declared `[context]` layer | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 46.8 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-09-20 — status reconciled after the fact (hollow landing)
  - `[medium]` `[patch]` The dispatched session (run `pyforge-marshal-20260920T083059668Z-b3ee2149`) landed the code but never wrote this spec's result: PR #1548 merged as `dbdb0773b1` with `CLAUDE.md` as its only changed file, this file still `backlog` with no Auto Run Result and no Tier-3 twin left behind once the worktree was removed. The run predates Story 53.1 (`spec-53-1`, merged `ab82437cd7`), whose prompt + guard now tell and gate a dispatched session to finish its spec like a loop session, and Story 53.2 (in flight) makes the landing reconcile from git facts. Reconciled here from the run journal and the merge itself — nothing below is remembered, every fact is cited.

## Auto Run Result

**Status:** done (reconstructed 2026-09-20 from the dispatch journal and `git`, after the fact — see the triage log)
**Summary:** `CLAUDE.md` gained `## Interactive session path`: the interactive Claude Code session on the shared checkout is the documented convenience path (`caveman-install --only claude --with-hooks` once per machine, `headroom wrap claude --code-memory none` per session), `marshal factory dispatch` / `spin` stay the measured path, no second kit and no separate benchmark (operator decision 2026-09-16, `spec-pyforge-marshal` CAP-195 ← `spec-marshal-token-economy` CAP-22), and retrieve/recall discipline replaces wholesale `epics.md` / PRD loads once the session is open (AGENTS.md § *Scribe recall (session path)*, `marshal context retrieve`).
**Verification:** journal `dispatch-verification` verdict `verified` (the station's `verify_commands`); `dispatch-land` PR #1548 → merged `dbdb0773b1` (`Merge pyforge-marshal/46-8 into main`); `dispatch-completion` verdict `completed`; baseline `4d165707d9` → final `dbdb0773b1`; story window 2026-09-20T08:30:59Z → 09:14:58Z.
**Files changed:** `CLAUDE.md` (+16, one section) — the PR's whole diff.
**Residual risks:** the AC's "demonstrably wrapped or seeded per the declared `[context]` layers" is documented, not machine-checked — the token-economy layers are still OFF fleet-wide (Epic 28 note), so the wrap is an operator step until they are switched on.
**Follow-up review recommendation:** false
