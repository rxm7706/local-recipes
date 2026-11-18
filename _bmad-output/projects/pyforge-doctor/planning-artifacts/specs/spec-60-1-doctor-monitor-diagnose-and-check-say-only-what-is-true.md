---
title: '60.1: doctor monitor, diagnose and check say only what is true'
type: 'fix'
created: '2026-11-18'
status: 'ready-for-dev'
story: 60-1-doctor-monitor-diagnose-and-check-say-only-what-is-true
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/warden.py'
  - 'src/shared/packages/pyforge-doctor/tests/**'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-doctor.md
  - docs/_STYLE_GUIDE.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `sources/atlas.py` reads `result.isError`, which the MCP SDK names `is_error`, so `monitor` and `diagnose` print an AttributeError before falling back; `sources/warden.py` tells the reader to run doctor from `-e pyforge-guild`, which does not carry warden.

**Approach:** The atlas source reads the attribute the installed SDK has (a test pins it against the SDK's own result type) and the warden message names only environments that carry warden.

Ledger key: `60-1-doctor-monitor-diagnose-and-check-say-only-what-is-true`.

### Living CAP citations

- spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** `sources/atlas.py` reads `result.isError`, which the MCP SDK names `is_error`, so `monitor` and `diagnose` print an AttributeError before falling back; `sources/warden.py` tells the reader to run doctor from `-e pyforge-guild`, which does not carry warden
**When** the atlas source reads the attribute the installed SDK has (a test pins it against the SDK's own result type) and the warden message names only environments that carry warden
**Then** `doctor monitor --fleet` prints no MCP AttributeError, the message names `pyforge-doctor` alone, and both doctor lanes exit 0
**And** doctor's items of `DW-doctor-59-5-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 60, minted with this story.
- Ledger key: `60-1-doctor-monitor-diagnose-and-check-say-only-what-is-true` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."60"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
