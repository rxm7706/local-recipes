---
title: '59.4: Design teaching is named; the pull cannot silently rot'
type: 'feature'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      The pulled deck does not yet state teaching-only except the two named
      exceptions (method-vs-machinery, project-context-as-constitution) --
      that is a Design-side content edit, and this session has no reachable
      Claude Design MCP connection (claude-design: FIRST_PARTY_AUTH_REJECTED,
      confirmed live this session) to make it.
    evidence: |-
      DW-VOCAB-2026-09-14-3's 2026-09-14 progress note: operator ruled
      "pull only -- no Design-side edits this pass" for the prior pull:
      (a), the Design-tier practice vocabulary entering no repo artifact
      (four-phases/three-tracks teaching), is explicitly still open and
      untouched by a pull.
    location: presentations/agentic-sdlc/project/Agentic SDLC.dc.html
    severity: medium
  - summary: >-
      Four unprefixed `quick-dev`/`dev-auto` mentions survived the 2026-09-14
      Design-side rename pass (one body line on Quick flow, three speaker
      notes on Quick flow / Workflow matrix); Paige and the four
      `bmad`-prefixed retired skill names are already gone (0 hits each).
    evidence: |-
      DW-VOCAB-2026-09-14-3's 2026-09-14 progress note, verified against the
      pulled deck rather than the entry's original claim.
    location: presentations/agentic-sdlc/project/Agentic SDLC.dc.html
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The deck teaches four-phases / three-tracks and is 13.5 KB behind.

**Approach:** The deck names itself teaching-only except method-vs-machinery and project-context-as-constitution. Retired BMAD skill names and Paige are gone from the pulled deck. A detector flags silent size/etag drift.

## Boundaries & Constraints

**Always:**
- Pulled deck states teaching-only except the two named exceptions.
- Retired BMAD skill names and Paige are absent from the pulled deck.
- A detector flags silent size/etag drift.

**Never:**
- Do not treat the whole deck as operational contract.
- Do not flip any Epic 44 blocked key.
- Do not label story modes L1–L5 or any autonomy percentage / maturity score.
  That is `spec-agentic-sdlc-autonomy` AUT-3 waiting on Charter §7; operator
  2026-09-16: teaching-only until the Guildhall exists.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| silent etag/size drift | pulled artifact diverges without a recorded pull | detector finding | finding |

</intent-contract>

## Binding

Parent Spec capability: `spec-vocabulary-one-name-one-job CAP-5`.
Surface: presentations/agentic-sdlc/; DW-VOCAB-2026-09-14-3. Herald executes the pull; steward wrote the ruling..
Ledger key: `59-4-design-teaching-is-named-the-pull-cannot-silently-rot`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-59-4-design-teaching-is-named-the-pull-cannot-silently-rot.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

