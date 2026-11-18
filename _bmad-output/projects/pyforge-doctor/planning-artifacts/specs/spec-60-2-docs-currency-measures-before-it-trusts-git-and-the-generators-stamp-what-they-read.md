---
title: '60.2: docs-currency measures before it trusts git, and the generators stamp what they read'
type: 'fix'
created: '2026-11-18'
status: 'done'
story: 60-2-docs-currency-measures-before-it-trusts-git-and-the-generators-stamp-what-they-read
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py'
  - 'src/shared/packages/pyforge-doctor/tests/**'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md'
  - 'scripts/_docs_gen_common.py'
  - 'scripts/docs_*.py'
  - 'tests/scripts/test_docs_*.py'
  - 'docs/map.yaml'
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

**Problem:** On a shallow clone every stamped page fails `source not found in git history`; when git cannot answer, the one WARN also hides unstamped pages; a generated row with no generator only warns; a generated stamp carries `-dirty` whenever anything in the tree is modified; five generators fail `ruff check`.

**Approach:** The source reports unstamped pages before any git-dependent check, reads a shallow repository as could-not-measure, fails a generated row with no generator, and the stamp's dirty flag is computed over the generator's own sources.

Ledger key: `60-2-docs-currency-measures-before-it-trusts-git-and-the-generators-stamp-what-they-read`.

### Living CAP citations

- spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** on a shallow clone every stamped page fails `source not found in git history`; when git cannot answer, the one WARN also hides unstamped pages; a generated row with no generator only warns; a generated stamp carries `-dirty` whenever anything in the tree is modified; five generators fail `ruff check`
**When** the source reports unstamped pages before any git-dependent check, reads a shallow repository as could-not-measure, fails a generated row with no generator, and the stamp's dirty flag is computed over the generator's own sources
**Then** the unit tests cover a shallow clone, an unreadable git with an unstamped page present, and a generator-less generated row; the six generators pass `ruff check` and `ruff format --check`; no stamp in `docs/map.yaml` ends in `-dirty` on a clean tree
**And** `DW-doctor-59-7-1` and the generator half of `DW-doctor-59-1-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-guild docs-gen-test && pixi run --frozen -e pyforge-guild docs-currency-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (as amended 2026-11-17), CAP-2 and CAP-3 (realized, no text change); FR-17 ← CAP-84; AD-1, AD-15.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 60, minted with this story.
- Ledger key: `60-2-docs-currency-measures-before-it-trusts-git-and-the-generators-stamp-what-they-read` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."60"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
