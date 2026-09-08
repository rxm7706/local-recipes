---
title: "pyforge-mason — Epic 32 cross-station retro (fleet consistency standard)"
date: 2026-09-07
station: pyforge-mason
epic: marshal Epic 32
spec: spec-fleet-consistency-standard
status: final
updated: "2026-09-07"
---

# pyforge-mason — fleet consistency standard, this station's part

**This is a cross-station retro, not an epic closeout.** The owning effort is marshal
Epic 32 (`spec-fleet-consistency-standard`); this records what changed *inside
pyforge-mason* and what its maintainer should know. The full effort retro lives at
`_bmad-output/projects/pyforge-marshal/planning-artifacts/retros/`.

## What changed here

`requires-python` raised `>=3.12` -> `>=3.14` with the platform floor folded into the PRD, spine and epics; `epics-with-stories.md` retired after an audit confirmed its OQ-E2/OQ-E5 open questions were already in `epics.md`. No test-tree move: mason already matched the standard (`unit/` + `integration/` + `meta/`).

## Verification

`pixi run -e pyforge-mason pyforge-mason-test` — **1579 passed, 3 deselected**. A green suite was the gate for
the commit that moved these files; the diff was never the gate.

Coverage was also measured for the first time (see the Spec's
`coverage-baseline-2026-09-07.md` companion). CI now gates this station's coverage on the
modules a PR *touches*, so pre-existing gaps report but do not red the build.

## What this station's maintainer should take from it

Mason needed the least work of the eight, and its five-tier skill cell is `conda-forge-expert` by design (Epic 11.1) -- an earlier by-hand audit mis-filed that absence as a gap until `five_tier.py` was actually run. The check was right; the human was not.

## Open for this station

Nothing blocking. The Spec's two open questions (mechanising INV-2/INV-3, and whether the
coverage `--cov` target should extend over the django/portal tier) are fleet-level and
tracked there, not here.
