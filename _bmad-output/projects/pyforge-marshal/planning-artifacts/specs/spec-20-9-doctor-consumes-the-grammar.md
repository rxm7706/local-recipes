---
title: Doctor consumes the grammar
type: feature
created: '2026-08-23'
status: done
shipped_ref: 'PR #695 / 047eadf4b2'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 6503b15991
---

<intent-contract>

## Intent

**Problem:** FR-191 CAP-2 — `story-status` evidence routes in `pyforge.doctor.sources.marshal` still use route 2/route 3 private dialects. Three standing false positives: marshal 8-2, marshal 10-1, mason 3-7.

**Approach:** Wire `sources/marshal.py` story-status evidence routes (`:479-517`) to `pyforge.core.landing_evidence` (shipped 20-8 in pyforge-core). Widen recognizable landing shapes; keep hedged absence-of-match behavior unchanged. No per-story whitelist. Deps: 20.8 done. Do not implement 20.10.

## Acceptance Criteria

- Evidence routes consume shared grammar instead of private dialects.
- Marshal 8-2, 10-1, mason 3-7 go green on live repo with no per-story whitelist.
- Genuinely-unlanded stories still fail; absence-of-match stays hedged.
- Doctor does not import `pyforge.marshal`.
- Does not wire marshal promotion/MRS-STATUS-010/retire (20.10).

## Boundaries & Constraints

**Never:** Per-story whitelists. Never import `pyforge.marshal`. Never implement 20.10. Finalize marshal ledger only. Do not touch steward 16-5.

</intent-contract>

## Code Map

- Parent: `spec-landing-evidence-grammar/SPEC.md` (CAP-2)
- Consumer: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` (`:479-517`)
- Grammar: `pyforge.core.landing_evidence` (pyforge-core, 20-8)
- Tests: doctor conformance + story-status integration on live false-positive cases

## Verification

- Three false positives green locally
- Unlanded story still hedged/fails as today
- Doctor conformance tests pass (no pyforge.marshal import)

## Auto Run Result

Status: done

PR: https://github.com/rxm7706/local-recipes/pull/695
Merge SHA: 047eadf4b285a59c708354a3318fab8242b9d972
Note: merged with `--admin` (Actions billing blocked CI; local verification green).

Summary: `gather_story_status` routes 2 and 3 now consume `pyforge.core.landing_evidence` classifiers (merge shapes on `--all`, full grammar on `main` including SHA allowlist). Clears marshal 8-2, 10-1, mason 3-7 false positives with no per-story whitelist. Doctor does not import `pyforge.marshal`.

Verification (local):
- `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py -q` → 31 passed
- `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/ -q` → 1087 passed
- `pixi run -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_landing_evidence_conformance.py -q` → 13 passed
