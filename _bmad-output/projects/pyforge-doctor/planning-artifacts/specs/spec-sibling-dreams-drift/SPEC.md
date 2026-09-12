---
spec: sibling-dreams-drift
status: in-progress
owner-dream: docs/dreams/sibling-dreams-drift.md
surface:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/sibling_dreams.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py
surface-drift-exclude:
  # 2026-09-12: also governed by spec-pyforge-doctor (the station kernel,
  # now clean), which reconciles this test file's routine changes. Coverage
  # is unchanged; only this spec's own drift tracking for it is off.
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py   # also governed by pyforge-doctor/spec-pyforge-doctor
companions: []
sources:
  - ../../../../../../docs/dreams/sibling-dreams-drift.md
open_questions: []
---

# SPEC — Sibling dreams directories don't drift silently

## Why
A sibling PyForge instantiation (OpenTeams mgmt-wf) shares this repo's
Dream convention — 13/15 dreams have local counterparts, independently
evolving, owners already diverging. Nothing detects it.

## Capabilities
- **CAP-1 — the drift check.** A doctor source diffs Dreams shared with the
  sibling tree (via the operator's token), joined on **filename** — the join
  the Dream itself asserts and the only one the two trees actually share;
  title is a reported axis alongside status, owner and content-hash, never
  the key. Warn-only, fail-open when unreachable, but an absent token emits
  `sibling-dreams-unreachable` rather than silence; surfaces in the doctor
  report + fleet-picture ATTENTION.
  *Success:* run against live data, the check names the divergences on the
  shared-filename set; offline yields `sibling-dreams-unreachable` and no
  error; a fixture alone does not satisfy this criterion.

## Constraints
Read-only, never a sync engine (reconciliation is human, per-dream); no
sibling content stored beyond titles/hashes (their prose is unlicensed);
degrades without the token, but says so rather than returning nothing.
The success criterion is proven against live data before the story closes —
the synthetic single-title fixture cannot reproduce the live failure and is
replaced by the real shared-filename shape measured 2026-09-09
(developer-machine-bootstrap, django-accelerator-framework,
enterprise-data-models-and-apis, miniforge-installer,
package-inventory-eligibility, pixi-container-image,
reusable-cicd-workflows).

## Non-goals
Bidirectional sync; importing dreams; watching any repo beyond the one
named sibling (a registry can come later if a third instantiation appears).

## Success signal
The ATTENTION block ambiently names sibling-diverged dreams the way it names
version drift — and goes quiet when the trees agree.

## Assumptions
- Story 16.1 shipped the source, but on the title key: measured live
  2026-09-09 with the operator's token, 131 local and 15 sibling Dreams
  parse, **0 shared titles** and 8 shared filenames — so the check as shipped
  cannot fire. `status: in-progress` reflects that; the Dream stays
  `specified` until the re-keyed check produces a live finding.
