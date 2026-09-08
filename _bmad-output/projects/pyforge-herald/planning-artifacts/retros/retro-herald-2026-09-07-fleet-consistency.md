---
title: "pyforge-herald — Epic 32 cross-station retro (fleet consistency standard)"
date: 2026-09-07
station: pyforge-herald
epic: marshal Epic 32
spec: spec-fleet-consistency-standard
status: final
updated: "2026-09-07"
---

# pyforge-herald — fleet consistency standard, this station's part

**This is a cross-station retro, not an epic closeout.** The owning effort is marshal
Epic 32 (`spec-fleet-consistency-standard`); this records what changed *inside
pyforge-herald* and what its maintainer should know. The full effort retro lives at
`_bmad-output/projects/pyforge-marshal/planning-artifacts/retros/`.

## What changed here

43 of its 47 test files sat loose at the tests root -- steward's CLI-contract concept with no directory at all -- and moved into `tests/unit/`. Five used `Path(__file__).resolve().parents[1]` to reach the package root and became `parents[2]`; `conftest.py` stayed at the tests root so shared fixtures remain visible. `requires-python` raised `>=3.12` -> `>=3.14`, and the platform floor was folded into the PRD, spine and epics.

## Verification

`pixi run -e pyforge-herald pyforge-herald-test` — **1254 passed, 4 skipped**. A green suite was the gate for
the commit that moved these files; the diff was never the gate.

Coverage was also measured for the first time (see the Spec's
`coverage-baseline-2026-09-07.md` companion). CI now gates this station's coverage on the
modules a PR *touches*, so pre-existing gaps report but do not red the build.

## What this station's maintainer should take from it

Herald was the station whose coverage was most misrepresented: the gate's suite map saw `tests/meta/` only, so it measured 4 of 47 files. Nothing was wrong with the tests -- they were invisible.

## Open for this station

Nothing blocking. The Spec's two open questions (mechanising INV-2/INV-3, and whether the
coverage `--cov` target should extend over the django/portal tier) are fleet-level and
tracked there, not here.
