---
title: '60.3: The shelf follows its own style guide, and the manticore and antigravity pages are supported pages'
type: 'fix'
created: '2026-11-18'
status: 'done'
story: 60-3-the-shelf-follows-its-own-style-guide-and-the-manticore-and-antigravity-pages-are-supported-pages
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'docs/how-to/**'
  - 'docs/reference/**'
  - 'docs/explanation/**'
  - 'docs/tutorials/**'
  - 'docs/map.yaml'
  - 'docs/MAP.md'
  - 'scripts/mirror-channels.py'
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

**Problem:** Pages use GitHub callouts where the style guide asks for admonitions; the getting-started tutorial does not follow the tutorial skeleton; the manticore page is a dated story record that documents an installer form the session hook denies; the antigravity page is one operator's dated notes; two feedstock pages are ten-line pointers registered as authored; existing pages do not link the 20 new ones; the purge runbook names a record nothing reads; `scripts/mirror-channels.py`'s docstring shows flags its parser rejects.

**Approach:** Each is corrected: admonitions, the tutorial skeleton, a manticore how-to written from the install that worked on 2026-11-18 (the lock's `bmad-method`), an antigravity how-to cut to what this repository wires and can check, pointers registered as pointers, cross-links, the purge list as the record of a purge, and the docstring matching the parser.

Ledger key: `60-3-the-shelf-follows-its-own-style-guide-and-the-manticore-and-antigravity-pages-are-supported-pages`.

### Living CAP citations

- spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** pages use GitHub callouts where the style guide asks for admonitions; the getting-started tutorial does not follow the tutorial skeleton; the manticore page is a dated story record that documents an installer form the session hook denies; the antigravity page is one operator's dated notes; two feedstock pages are ten-line pointers registered as authored; existing pages do not link the 20 new ones; the purge runbook names a record nothing reads; `scripts/mirror-channels.py`'s docstring shows flags its parser rejects
**When** each is corrected: admonitions, the tutorial skeleton, a manticore how-to written from the install that worked on 2026-11-18 (the lock's `bmad-method`), an antigravity how-to cut to what this repository wires and can check, pointers registered as pointers, cross-links, the purge list as the record of a purge, and the docstring matching the parser
**Then** `docs-currency-check`, `docs-map-hygiene-check` and `docs-site-validate` exit 0; both the manticore and the antigravity pages stay registered authored pages (operator ruling: both stay supported)
**And** `DW-doctor-59-3-2` and the documentation items of `DW-doctor-59-3-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-currency-check && pixi run --frozen -e pyforge-guild docs-map-hygiene-check && pixi run --frozen -e site docs-site-validate
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 60, minted with this story.
- Ledger key: `60-3-the-shelf-follows-its-own-style-guide-and-the-manticore-and-antigravity-pages-are-supported-pages` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."60"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
