---
title: '60.4: Doctor''s chain closes: CAP-84 reads shipped and the incident log''s home is settled'
type: 'fix'
created: '2026-11-18'
status: 'done'
story: 60-4-doctor-s-chain-closes-cap-84-reads-shipped-and-the-incident-log-s-home-is-settled
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml'
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

**Problem:** CAP-84 still reads ready and Story 59.8 review because the doctor `SPEC.md` could not be re-derived in the session; doctor's incident log stays in its package because a marshal capability names the path.

**Approach:** The operator runs the one re-derive script the session prepared (or allows the write), the doctor ledger's rows read resolved, and the incident log's package home is recorded as the decision it is.

Ledger key: `60-4-doctor-s-chain-closes-cap-84-reads-shipped-and-the-incident-log-s-home-is-settled`.

### Living CAP citations

- spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** CAP-84 still reads ready and Story 59.8 review because the doctor `SPEC.md` could not be re-derived in the session; doctor's incident log stays in its package because a marshal capability names the path
**When** the operator runs the one re-derive script the session prepared (or allows the write), the doctor ledger's rows read resolved, and the incident log's package home is recorded as the decision it is
**Then** CAP-84 reads shipped, Story 59.8 done, and `chain-completeness-check` and `story-status-check` exit 0
**And** `DW-doctor-59-4-1`'s incident-log half and Story 59.8 reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild chain-completeness-check && pixi run --frozen -e pyforge-guild story-status-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 60, minted with this story.
- Ledger key: `60-4-doctor-s-chain-closes-cap-84-reads-shipped-and-the-incident-log-s-home-is-settled` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."60"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
