---
title: 'Extract detector in detectors-ci'
type: 'feature'
created: '2026-09-13'
status: 'done'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A 20k truncate of `SPEC.md` keeps Why and drops
Capabilities. Wholesale bodies blow the token budget.

**Approach:** Doctor gather in `detectors-ci` reads CAP heading +
intent/success only (Scribe 13.1 / 14.1 shape). HARD on
unclassified `CAP-N` and `A-only` without expiry.

## Boundaries & Constraints

**Always:**
- Extract contract is `extract.md`.
- Post-PIN unclassified paths are `--append`.

**Never:**
- Never inventory via `_node_from_text_file` on `SPEC.md`.
- Never flip 44.1.

</intent-contract>

## Acceptance Criteria

1. Fixture SPEC: detector sees `CAP-9`, not a unique Why sentence.
2. Unclassified `CAP-N` is HARD.
3. `A-only` without expiry is HARD.
4. Post-PIN file without a row is `--append`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7c990d5b32` (2026-09-13, "Merge pull request #1347 from rxm7706/steward-55-2-extract-detector"). Ledger row `55-2-extract-detector-in-detectors-ci: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-55-2-extract-detector-in-detectors-ci.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `pixi.toml`, `scripts/detectors.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py`, `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py` (+3 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
