---
title: '126.6: Every row this change opened is closed, and the preflight is green with fewer skips'
type: 'fix'
created: '2026-11-18'
status: 'done'
story: 126-6-every-row-this-change-opened-is-closed-and-the-preflight-is-green-with-fewer-skips
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - '_bmad-output/projects/pyforge-*/planning-artifacts/deferred-work-ledger.md'
  - 'scripts/.spec-surface-baseline.json'
  - '_bmad-output/projects/pyforge-*/planning-artifacts/specs/spec-pyforge-*/.memlog.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Epics 59 and 125 opened eleven deferred-work rows and the operator ruled that none is left for later.

**Approach:** Each row reads resolved with its commit (or names the one operator act left), every governing Spec is reconciled and stamped, and the full preflight is run on the final head.

Ledger key: `126-6-every-row-this-change-opened-is-closed-and-the-preflight-is-green-with-fewer-skips`.

### Living CAP citations

- spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** Epics 59 and 125 opened eleven deferred-work rows and the operator ruled that none is left for later
**When** each row reads resolved with its commit (or names the one operator act left), every governing Spec is reconciled and stamped, and the full preflight is run on the final head
**Then** `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` exits 0 on macOS and PR #2373's CI is green
**And** every row of `DW-doctor-59-*` and `DW-steward-125-*` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 126, minted with this story.
- Ledger key: `126-6-every-row-this-change-opened-is-closed-and-the-preflight-is-green-with-fewer-skips` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."126"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
