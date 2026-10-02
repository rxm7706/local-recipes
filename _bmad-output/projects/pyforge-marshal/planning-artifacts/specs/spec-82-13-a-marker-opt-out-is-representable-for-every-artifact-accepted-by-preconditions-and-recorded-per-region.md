---
title: '82.13: A marker opt-out is representable for every artifact, accepted by preconditions, and recorded per region'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-8-5-marker-deletion-as-a-sanctioned-opt-out.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** FR-112 makes deleting a managed region's markers a permanent opt-out; three gaps (the Story 8.5 family) keep
it from holding end to end. Re-verified at HEAD a7cdb91fe4:

- `seed/state/schema.json` types `managed[].id` as `nonBlankString` (`:59`, pattern `\S`, so spaces and `#` are legal),
  while the `opted_out` item pattern is `^[^\s#]+#[a-z0-9][a-z0-9-]*` (`:78`). Its description (`:75`) claims the artifact
  half is "deliberately as permissive as managed[].id"; it is stricter, so `record_opt_out(state, "has a space", ...)`
  raises and a legally named artifact cannot be opted out. `ManifestEntry` requires only a non-blank id. No manifest id in
  the fleet trips it today; every real id is a slug (DW-FU-8-5-2).
- `seed/verbs/preconditions.py` never reads `opted_out` (zero occurrences); rung 6 reports a deleted region as
  "recorded managed region is missing from the file" (`:445`) under `managed-content-modified`, whose remedy tells the
  operator to revert the deletion or `--force`. `seed/verbs/adopt.py:1002-1003` already feeds `state.opted_out` to
  `build_plan`, and `adopt`, `update` (`:1061`) and `init` (`:484`) all call `check_preconditions`, so the two halves
  contradict each other on FR-112's own scenario (DW-FU-8-5-5).
- `managed[]` holds at most one entry per id (`seed/state/store.py:609`, `_reject_duplicates` at `:326`) and each entry
  exactly one nullable `inserted_region_span` (`schema.json:107`). A hybrid artifact with several declared regions can
  record one span, so `detect/optout.py` honours a deleted region's opt-out for at most one region and its siblings fall to
  `MISSING`, whose remedy re-inserts them (DW-FU-8-5-6).

**Approach:**

- One artifact-id grammar: `ManifestEntry.id` and `managed[].id` both reject whitespace and `#` (the `opted_out` artifact
  half's grammar, defined once in the schema and once in code); the schema description says so. A state file carrying such
  an id reads as `state-invalid`, as any schema violation does.
- Rung 6 skips a recorded region whose `<id>#<region>` is opted out, recorded in `state.opted_out` or derived by
  `detect/optout.py`; the verbs pass the opt-out set alongside the managed records.
- State records a span per installed region of a hybrid artifact (a list keyed by region name); the store reads the old
  one-span shape as a one-region list and writes the new shape, so a derived opt-out covers each deleted region on its
  own.

Ledger key: `82-13-a-marker-opt-out-is-representable-for-every-artifact-accepted-by-preconditions-and-recorded-per-region`.
Type / Effort / Deps: fix / L / 82.12.

### Living CAP citations

- `spec-pyforge-marshal` CAP-11 (deleting the markers is recorded as a permanent opt-out that later runs respect) and CAP-17
  (the genesis-owned state file), with Story 8.5 (FR-112; AD-58) and Story 10.2 (the state schema and store). Defects of
  shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a manifest entry whose id contains a space or `#` When the manifest loads Then it fails with an error naming the entry
- Given every artifact id the shipped manifest declares When an opt-out is recorded for any of its regions Then the state validates
- Given a state whose `opted_out` holds `<id>#<region>` and a file whose region markers were deleted When `adopt`, `update` or `init` runs Then rung 6 does not report that region missing and no `--force` is needed
- Given a hybrid artifact with two declared regions whose markers were both deleted When detection runs and the state is written and read back Then both regions are opted out and neither is planned for insertion
- Given a state file in the old one-span shape When it is read Then it loads as a one-region list and the next write uses the new shape
- Given each fix reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** The state stays schema-validated at runtime (FR-104). An opt-out stays permanent until an explicit reinstate.
Close DW-FU-8-5-2, DW-FU-8-5-5 and DW-FU-8-5-6 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not loosen the region-name grammar. Do not drop the old state shape without reading it. Do not change the
plan fingerprint, rung 5 or `--skip` (Story 82.12's surface).

</intent-contract>

## Binding

Parent: Stories 8.5 and 10.2, `spec-pyforge-marshal` CAP-11 and CAP-17; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-13-a-marker-opt-out-is-representable-for-every-artifact-accepted-by-preconditions-and-recorded-per-region`.
Ledger status at mint: `backlog`.
Deps: 82.12 (both edit `seed/verbs/preconditions.py` and the verbs).
Closes: DW-FU-8-5-2, DW-FU-8-5-5, DW-FU-8-5-6.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
