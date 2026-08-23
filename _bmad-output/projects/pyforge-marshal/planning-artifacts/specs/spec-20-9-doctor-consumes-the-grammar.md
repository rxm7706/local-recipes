---
title: Doctor consumes the grammar
type: feature
created: '2026-08-23'
status: ready
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
