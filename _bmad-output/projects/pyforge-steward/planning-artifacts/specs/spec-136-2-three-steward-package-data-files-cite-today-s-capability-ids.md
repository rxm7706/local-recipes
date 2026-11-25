---
title: '136.2: Three steward package-data files cite today''s capability ids'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 136-2-three-steward-package-data-files-cite-today-s-capability-ids
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/data/sprint-ledger-query.schema.json'
  - 'src/shared/packages/pyforge-steward/measures/measures.yaml'
  - 'src/shared/packages/pyforge-steward/catalog/catalog.yaml'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
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

**Problem:** `DW-steward-122-4-1`. `sprint-ledger-query.schema.json:5` cites `spec-sprint-ledger-query-module CAP-4` (today spec-pyforge-steward:CAP-148), `measures/measures.yaml:1` cites `spec-build-league-scorecard CAP-2` (today CAP-45) and `catalog/catalog.yaml:1` cites `spec-self-hosted-bmad-marketplace CAP-1` (today CAP-117). `oracle-map.md`'s CAP-179 row note still says `test_cap_citations.py` holds help and output only, though since Story 122.4 it also holds every comment and docstring under the package's `src` and `tests`.

**Approach:** Re-key the three citations by the provenance map `test_cap_citations.py` already holds, extend that test to read these three files so the ids cannot drift back, check whether a consumer pins the schema's `description` text before changing it, and amend the oracle-map note.

Ledger key: `136-2-three-steward-package-data-files-cite-today-s-capability-ids`.

### Living CAP citations

- spec-pyforge-steward CAP-179 (the public contract and the ids the package cites; realized, no text change; its `oracle-map.md` row note is amended); reads CAP-148, CAP-45 and CAP-117 (no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change a schema key, a measure or a catalog entry; only the citing comment or description moves.
- Never change the schema's `$id`.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-122-4-1` reports three package-data files that cite an absorbed Spec's capability id and an `oracle-map.md` note that understates what `test_cap_citations.py` holds
**When** each citation is re-keyed to the station Spec's id by the provenance map and the test reads the three files
**Then** no file under the steward package cites `spec-sprint-ledger-query-module`, `spec-build-league-scorecard` or `spec-self-hosted-bmad-marketplace` as a live id, the three files cite spec-pyforge-steward:CAP-148, CAP-45 and CAP-117, and a test fails when one of them cites an absorbed Spec again
**And** `oracle-map.md`'s CAP-179 row note says the test holds help, output, comments, docstrings and the three data files, and the row reads resolved

- **AC1 — No absorbed-Spec id is left in the three files.** Expected: exit 1 (no line matches).

  ```bash
  grep -n -E 'spec-sprint-ledger-query-module CAP|spec-build-league-scorecard CAP|spec-self-hosted-bmad-marketplace CAP' src/shared/packages/pyforge-steward/src/pyforge/steward/data/sprint-ledger-query.schema.json src/shared/packages/pyforge-steward/measures/measures.yaml src/shared/packages/pyforge-steward/catalog/catalog.yaml
  ```

- **AC2 — The citation test holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_cap_citations.py -q
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-179 (the public contract and the ids the package cites; realized, no text change; its `oracle-map.md` row note is amended); reads CAP-148, CAP-45 and CAP-117 (no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-2-three-steward-package-data-files-cite-today-s-capability-ids`.
- Deferred-work row: `DW-steward-122-4-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
