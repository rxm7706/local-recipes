---
title: "pyforge-warden — Epic 32 cross-station retro (fleet consistency standard)"
date: 2026-09-07
station: pyforge-warden
epic: marshal Epic 32
spec: spec-fleet-consistency-standard
status: final
updated: "2026-09-07"
---

# pyforge-warden — fleet consistency standard, this station's part

**This is a cross-station retro, not an epic closeout.** The owning effort is marshal
Epic 32 (`spec-fleet-consistency-standard`); this records what changed *inside
pyforge-warden* and what its maintainer should know. The full effort retro lives at
`_bmad-output/projects/pyforge-marshal/planning-artifacts/retros/`.

## What changed here

`tests/conformance/` (19 oracle and engine gates -- dogfood, corpus determinism, perf, parallelism) folded into `tests/integration/`, which is their real weight; `test_smoke.py` moved to `tests/unit/`. `requires-python` raised to `>=3.14`.

## Verification

`pixi run -e pyforge-warden pyforge-warden-test` — **2114 passed, 11 deselected**. A green suite was the gate for
the commit that moved these files; the diff was never the gate.

Coverage was also measured for the first time (see the Spec's
`coverage-baseline-2026-09-07.md` companion). CI now gates this station's coverage on the
modules a PR *touches*, so pre-existing gaps report but do not red the build.

## What this station's maintainer should take from it

Warden and steward independently chose the same directory name for different concepts -- CLI contracts at unit level versus oracle gates at integration level. The fold had to be by test LEVEL, not by name; folding on the shared name would have put perf and corpus-determinism gates in the unit suite.

## Open for this station

Nothing blocking. The Spec's two open questions (mechanising INV-2/INV-3, and whether the
coverage `--cov` target should extend over the django/portal tier) are fleet-level and
tracked there, not here.
