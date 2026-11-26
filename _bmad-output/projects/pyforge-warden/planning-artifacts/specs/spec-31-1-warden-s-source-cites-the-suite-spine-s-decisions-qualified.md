---
title: '31.1: Warden''s source cites the suite spine''s decisions qualified'
type: 'fix'
created: '2026-11-26'
status: 'done'
story: 31-1-warden-s-source-cites-the-suite-spine-s-decisions-qualified
spec: spec-pyforge-warden
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/models.py'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/report.py'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** warden's spine defines no `AD-n` at all, and its source cites `suite:AD-4`, `suite:AD-9` and `suite:AD-10` bare in five modules. All three are decisions of the suite spine (advisory lenses never gate; one module roster; cross-station prerequisites are checks), which the TEA advisory realizes.

**Approach:** Write each such tag with the prefix of the spine it means (`suite:AD-4`, `suite:AD-9`, `suite:AD-10`). Each was judged from its context against the spines' own headings, not by number alone.

Ledger key: `31-1-warden-s-source-cites-the-suite-spine-s-decisions-qualified`.

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

**Given** five warden modules cite the suite spine's `suite:AD-4`, `suite:AD-9` and `suite:AD-10` bare, and warden's own spine defines none
**When** each is written with the prefix of the spine it means (`suite:AD-4`, `suite:AD-9`, `suite:AD-10`)
**Then** `ad-citation-check` reports no undefined bare tag in warden's source
**And** warden's suites pass with no behaviour changed

- **AC1 — The detector is green on the tree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild ad-citation-check
  ```

- **AC2 — Warden's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-warden pyforge-warden-test
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent only. The review confirmed all three rewrites against the suite spine's headings and found no bare tag left. Two of the rewrites are in a runtime message (`tea_advisory.py`); no test or contract file carried the old wording.
