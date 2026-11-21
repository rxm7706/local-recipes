---
title: '34.1: The src/platform import guard reads code, not text'
type: 'fix'
created: '2026-11-21'
status: 'done'
story: 34-1-the-src-platform-import-guard-reads-code-not-text
spec: spec-pyforge-scribe
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py'
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - docs/dreams/pyforge-scribe.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `test_src_platform_has_no_pyforge_import` also asserts that the branch's `src/platform` diff text never contains `import pyforge` or `from pyforge`, so an edit within three lines of a string that mentions the phrase reds the suite though no import was added.

**Approach:** The text search is removed and the AST walk over every changed `.py` file is the guard, as in steward's twin.

Ledger key: `34-1-the-src-platform-import-guard-reads-code-not-text`.

### Living CAP citations

- spec-pyforge-scribe CAP-31 (realized, no text change); relay of spec-pyforge-steward:CAP-175.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never let a real `pyforge` import under `src/platform/` pass, or change another station's guard.

## Acceptance Criteria

**Given** `test_src_platform_has_no_pyforge_import` also asserts that the branch's `src/platform` diff text never contains `import pyforge` or `from pyforge`, so an edit within three lines of a string that mentions the phrase reds the suite though no import was added
**When** the text search is removed and the AST walk over every changed `.py` file is the guard, as in steward's twin
**Then** a real `import pyforge…` or `from pyforge…` statement added under `src/platform/` still fails the guard, a string that mentions the phrase does not, and a test proves both
**And** scribe's live-tree half passes

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pyforge-scribe-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-scribe CAP-31 (realized, no text change); relay of spec-pyforge-steward:CAP-175.
- Dream: `docs/dreams/pyforge-scribe.md` § *Realization log*, the 2026-11-21 entry; operator, 2026-11-21: "fix the scribe guard too".
- Epic: Epic 34, minted with this story.
- Ledger key: `34-1-the-src-platform-import-guard-reads-code-not-text` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."34"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's 2026-11-21 entry and the operator, 2026-11-21: "fix the scribe guard too"; done on branch `corridor-platform-host-2026-11-21` (PR #2375).
