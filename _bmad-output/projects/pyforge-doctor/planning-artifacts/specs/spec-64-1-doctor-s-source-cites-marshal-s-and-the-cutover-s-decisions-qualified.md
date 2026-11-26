---
title: '64.1: Doctor''s source cites marshal''s and the cutover''s decisions qualified'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 64-1-doctor-s-source-cites-marshal-s-and-the-cutover-s-decisions-qualified
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/bare_merge.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/pyforge-doctor.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** doctor's source cites decisions it judges marshal against as bare `AD-n`: the merge-subject form, configuration provenance and materialized policy are marshal's `pyforge-marshal:AD-24`, `pyforge-marshal:AD-16`, `pyforge-marshal:AD-12` and `pyforge-marshal:AD-35`, and the per-capability freeze rule is the cutover spine's `fnd:AD-22`. Doctor's own spine has an unrelated `AD-12`, so one of them read as doctor's.

**Approach:** Write each such tag with the prefix of the spine it means (`pyforge-marshal:AD-n` for marshal's, `fnd:AD-22` for the cutover's). Each was judged from its context against the spines' own headings, not by number alone.

Ledger key: `64-1-doctor-s-source-cites-marshal-s-and-the-cutover-s-decisions-qualified`.

### Living CAP citations

- spec-one-chain-per-station:CAP-9 (the chain standard is one page, and that page holds the id grammar; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change behaviour, an exit code or a flag.
- Never qualify a tag that means this station's own spine.

## Acceptance Criteria

**Given** five doctor modules cite marshal's and the cutover spine's decisions bare, one of them a number doctor's own spine also defines
**When** each is written with the prefix of the spine it means (`pyforge-marshal:AD-n` for marshal's, `fnd:AD-22` for the cutover's)
**Then** `ad-citation-check` reports no undefined bare tag in doctor's source
**And** doctor's suites pass with no behaviour changed

- **AC1 — The detector is green on the tree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild ad-citation-check
  ```

- **AC2 — Doctor's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-test
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent only. The review confirmed the marshal and cutover rewrites against their headings (`pyforge-marshal:AD-16` from its heading only). Not checked: whether a bare tag in doctor's own range means marshal's.
