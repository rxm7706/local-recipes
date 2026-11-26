---
title: '123.1: The citation detector holds station source to the tag rule'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 123-1-the-citation-detector-holds-station-source-to-the-tag-rule
spec: spec-pyforge-marshal
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a citation detector in detectors-ci; a gated detector is a silent green (roster list)
surface:
  - 'scripts/ad_citation_check.py'
  - 'tests/scripts/test_ad_citation_check.py'
  - 'docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `ad-citation-check` holds planning prose to the tag rule and never reads station source. Doctor, steward and warden cite decisions of other spines as bare `AD-n`; some of those numbers also exist in the citing station's own spine, so the reader is sent to the wrong decision.

**Approach:** Scan each package's `src` against its home project's defined decisions (the project of the package's name; marshal's for the two kernel packages) and report an undefined bare tag through the existing ratchet. Treat `canopy AD-n` (a fixed list of spine prefixes followed by a space) as qualified. Do not scan tests. Record where a bare tag may stand in the chain standard's id table.

Ledger key: `123-1-the-citation-detector-holds-station-source-to-the-tag-rule`.

### Living CAP citations

- spec-one-chain-per-station:CAP-9 (the chain standard is one page, and that page holds the id grammar; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never add a baseline entry for a source finding.
- Never treat an arbitrary word before `AD-n` as a qualifier.

## Acceptance Criteria

**Given** the detector reads planning prose only
**When** it also scans station source against each package's home project
**Then** an undefined bare tag in source is a finding; a qualified one is not; a kernel package is held to marshal's spine
**And** the tree is green with no source baseline

- **AC1 — The detector's tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest tests/scripts/test_ad_citation_check.py -q
  ```

- **AC2 — The detector is green on the tree.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild ad-citation-check
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent only. Applied from the review: source findings are kept out of the baseline (a test holds that the committed baseline has no source row); a qualified tag is resolved too (an unknown prefix or an id its spine lacks is a finding); `canopy` is the one space qualifier (the only one the tree uses), so a sentence in which the word suite happens to precede a tag reads as bare; a package with no home project is a finding; the real `_SOURCE_HOME` is pinned. Not done here: `django-*` portals and non-Python files are not scanned (`django-pyforge` cites 43 bare tags, marshal's JSON data files 76), and `_bmad/custom/bmad-review.toml` still names a bare roster tag. A bare number two spines both define stays invisible to the check.
