---
title: '`dreams-hygiene` reconciles every Dream file, and README:71 is enforced'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `_parse_readme_dream_statuses` reconciles only Dreams that already carry
a `docs/dreams/README.md` row, so **61 of 131** Dream files are invisible to the
detector while it reports `ok`. `readme-table-orphan` is one-directional by design —
it catches rows pointing at missing files, never files missing a row. Three separate
gaps compound this: `docs/dreams/README.md:71`'s own rule (a Dream at `status:
specified` whose Spec is not `ready` or beyond should be reported) is not enforced —
today `django-accelerator-framework` violates it and passes both `dream-chain-check`
and `dream-chain --dreams`; Kinship `[[…]]` wikilinks are never validated against
`docs/dreams/`, so broken links go unnoticed (the 2026-09-09 currency review found
some); and files-without-a-row is simply unmeasured.

**Approach:** Derive reconciliation from the Dream files themselves rather than from
the README's own (incomplete) table, treating the README as the incomplete map it is.
Add three new classes: (1) a Dream file with no README row is a named warn-only
finding; (2) README:71's rule is enforced as a named finding; (3) every `[[…]]`
Kinship wikilink is resolved against `docs/dreams/`, with an unresolvable target
warned by name. Each class ships with a fixture proving it fires **and** a measured
count against the live tier, so a class that would flood the report is narrowed
before it joins `detectors` rather than after.

## Boundaries & Constraints

**Always:**
- Reconciliation is derived from the Dream files themselves, not solely from the
  README table.
- Each of the three new classes (file-missing-a-row, README:71 violation, broken
  Kinship wikilink) is warn-only.
- Each class ships with both a fixture proving it fires and a measured count against
  the live tier before it joins `detectors`, so a flood-prone class is narrowed first.
- README:71's rule (a Dream at `status: specified` whose Spec is not `ready` or beyond
  is reported) is enforced as its own finding, verified against the live
  `django-accelerator-framework` case.
- Every `[[…]]` Kinship wikilink is resolved against `docs/dreams/`; an unresolvable
  target names the source file and the dead link.

**Never:**
- `readme-table-orphan`'s existing one-directional behavior (rows pointing at missing
  files) is not removed or altered by this story — the new classes are additive.
- No new class ships without both a fixture and a measured live-tree count.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dream file with no README row | Any of the 61 Dream files missing a `docs/dreams/README.md` row | Named warn-only finding | n/a |
| README:71 violation | `django-accelerator-framework`: `status: specified`, Spec not `ready` or beyond | Named finding (today passes both `dream-chain-check` and `dream-chain --dreams` silently) | n/a |
| Broken Kinship wikilink | A `[[…]]` target that does not resolve against `docs/dreams/` | Warn naming the source file and the dead link | n/a |
| Dream file with a README row, no violations | Normal, reconciled Dream | No finding | n/a |
| Flood-prone class at measurement time | A candidate class whose live-tree count is too high to be useful | Narrowed before joining `detectors`, not after | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — `_parse_readme_dream_statuses` (`:891`) and the `dreams-hygiene` gather around it.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain.py` — fixtures and measured-count tests for each of the three new classes.

## Tasks & Acceptance

**Execution:**
- `feature` — derive Dream reconciliation from the files under `docs/dreams/` themselves, not only from the README table rows.
- `feature` — add a "Dream file with no README row" warn-only finding class.
- `feature` — enforce `docs/dreams/README.md:71`'s rule as a named finding, verified against the live `django-accelerator-framework` case.
- `feature` — resolve every `[[…]]` Kinship wikilink against `docs/dreams/`; warn-name unresolvable targets.
- `feature` — add a fixture and a measured live-tier count for each of the three new classes before wiring it in.

**Acceptance Criteria:**
- Given `_parse_readme_dream_statuses` reconciles only Dreams that already carry a README row, so 61 of 131 Dream files are invisible while the detector reports `ok`, when reconciliation is derived from the Dream files themselves and the README is treated as the incomplete map it is, then a Dream file with no README row is a named warn-only finding.
- `docs/dreams/README.md:71` is enforced — a Dream at `status: specified` whose Spec is not at `ready` or beyond is reported (today `django-accelerator-framework` violates it and passes both `dream-chain-check` and `dream-chain --dreams`).
- Every `[[…]]` Kinship wikilink is resolved against `docs/dreams/` and an unresolvable target is a warn naming the source file and the dead link.
- Each of the three new classes ships with a fixture proving it fires and a measured count against the live tier, so a class that would flood the report is narrowed before it joins `detectors` rather than after.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
