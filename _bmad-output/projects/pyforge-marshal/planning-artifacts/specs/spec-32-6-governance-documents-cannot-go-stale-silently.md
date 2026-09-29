---
title: '32.6: Governance documents cannot go stale silently'
type: 'feature'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Governance documents cannot go stale silently (contract recovered from epics.md Intent + ACs).

**Approach:** `scripts/governance_currency_check.py` (net-new), `pixi.toml` (`[feature.local-recipes.tasks.governance-currency]`). *(Corrected during implementation: the `SCRIPTS`-list meta-test governs the CFE skill's own `.claude/skills/conda-forge-expert/scripts/`, not repo-root `scripts/`, so a repo-root detector needs no entry there — `scripts/detectors.py` discovers it from the filesystem via its `DETECTOR = {"scope": "repo"}` declaration.)*

Ledger key: `32-6-governance-documents-cannot-go-stale-silently`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / M / S-32.1.

### Living CAP citations

- Living: `spec-pyforge-marshal CAP-112` ← `spec-fleet-consistency-standard CAP-6`.

## Acceptance Criteria

- Given the removed 16-stage table named four non-existent skills for two BMAD versions with no gate noticing — the same class of defect INV-4 identified for detectors, applied to the prose that governs them When a detector resolves every `bmad-*` skill name, script path and file reference in `EXEMPLAR-STANDARD.md`, `AGENTS.md`, `CLAUDE.md` and `docs/reference/test-charter.md` Then it exits non-zero naming each reference that no longer resolves, is discovered by `scripts/detectors.py` from the filesystem, and run against the standard as it stood on 2026-09-07 reproduces all seven staleness findings this session found by hand And deliberate historical citations (a name quoted precisely because it was removed) are exempted by an explicit `governance-currency:ignore-start/end` marker, never by a silent heuristic — an unmarked dead reference must fail

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the removed 16-stage table named four non-existent skills for two BMAD versions  | a detector resolves every `bmad-*` skill name, script path a | it exits non-zero naming each reference that no longer resolves, is discovered b | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 32.6 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `32-6-governance-documents-cannot-go-stale-silently: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
