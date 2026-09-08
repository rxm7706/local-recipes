---
title: "pyforge-steward — Epic 32 cross-station retro (fleet consistency standard)"
date: 2026-09-07
station: pyforge-steward
epic: marshal Epic 32
spec: spec-fleet-consistency-standard
status: final
updated: "2026-09-07"
---

# pyforge-steward — fleet consistency standard, this station's part

**This is a cross-station retro, not an epic closeout.** The owning effort is marshal
Epic 32 (`spec-fleet-consistency-standard`); this records what changed *inside
pyforge-steward* and what its maintainer should know. The full effort retro lives at
`_bmad-output/projects/pyforge-marshal/planning-artifacts/retros/`.

## What changed here

`tests/conformance/` (32 CLI-verb contract tests) folded into `tests/unit/`; `conformance/fixtures/` moved to the standard `tests/fixtures/` with three `Path(__file__).parent` lookups becoming `.parent.parent`. `epics.md:74` -- the normative test-tier declaration, not just the files -- was rewritten. `requires-python` raised to `>=3.14`.

## Verification

`pixi run -e pyforge-steward pyforge-steward-test` — **1197 passed**. A green suite was the gate for
the commit that moved these files; the diff was never the gate.

Coverage was also measured for the first time (see the Spec's
`coverage-baseline-2026-09-07.md` companion). CI now gates this station's coverage on the
modules a PR *touches*, so pre-existing gaps report but do not red the build.

## What this station's maintainer should take from it

Steward's suite-shape mandate was found by accident inside `epics-with-stories.md`, the file being retired. That near-miss is why the audit of all eight was made a gate rather than a formality: normative content had accumulated in a file everyone treated as derived.

## Open for this station

Nothing blocking. The Spec's two open questions (mechanising INV-2/INV-3, and whether the
coverage `--cov` target should extend over the django/portal tier) are fleet-level and
tracked there, not here.
