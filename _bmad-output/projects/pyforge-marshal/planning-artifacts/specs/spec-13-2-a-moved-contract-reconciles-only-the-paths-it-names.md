---
title: '13.2: A moved contract reconciles only the paths it names'
type: 'change'
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

**Problem:** As the operator, I want a memlog entry to stop speaking for governed files it never mentions, So that unrelated activity cannot silently launder pending drift.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `13-2-a-moved-contract-reconciles-only-the-paths-it-names`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: change / M / —.

### Living CAP citations

- Cited from epics.md: FR-165, FR-167

## Acceptance Criteria

- Given a spec whose memlog moved and whose governed files drifted When the drift pass runs Then a drifted file named in the memlog clears, and an unnamed one reports `[drift-presumed]` And `[drift-presumed]` is informational — it never contributes to the exit code And a memlog naming no paths is still legal: every drifted file degrades to `[drift-presumed]`, never to a hard failure (or the gate reds for every historical entry) And matching is literal substring on the repo-relative path — no prose inference And no `.memlog.md` is edited, reordered, or normalized by this change And a laundering test replays the live incident — appending an unrelated entry to `spec-regenerable-factory`'s memlog no longer clears the drift on `scripts/bmad_drift_check.py` / `scripts/dream_chain_check.py` And a mutation test proves it both ways: restoring the per-spec short-circuit re-reds that laundering test

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| a spec whose memlog moved and whose governed files drifted | the drift pass runs | a drifted file named in the memlog clears, and an unnamed one reports `[drift-pr | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 13.2 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `ab0cb3b2a0` (2026-09-11, "retro(cfe): Story 13.2 G26 dbgpt-client upper-bound cap case study (v8.90.2)"). Ledger row `13-2-a-moved-contract-reconciles-only-the-paths-it-names: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/conda-forge-expert/CHANGELOG.md`, `.claude/skills/conda-forge-expert/MANIFEST.yaml`, `.claude/skills/conda-forge-expert/SKILL.md`, `.claude/skills/conda-forge-expert/config/skill-config.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
