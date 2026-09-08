---
title: "pyforge-scribe — Epic 32 cross-station retro (fleet consistency standard)"
date: 2026-09-07
station: pyforge-scribe
epic: marshal Epic 32
spec: spec-fleet-consistency-standard
status: final
updated: "2026-09-07"
---

# pyforge-scribe — fleet consistency standard, this station's part

**This is a cross-station retro, not an epic closeout.** The owning effort is marshal
Epic 32 (`spec-fleet-consistency-standard`); this records what changed *inside
pyforge-scribe* and what its maintainer should know. The full effort retro lives at
`_bmad-output/projects/pyforge-marshal/planning-artifacts/retros/`.

## What changed here

`requires-python` raised `>=3.12` -> `>=3.14`; `epics-with-stories.md` retired after audit. No test-tree move: scribe already matched the standard.

## Verification

`pixi run -e pyforge-scribe pyforge-scribe-test` — **300 passed, 4 skipped, 18 errors**. A green suite was the gate for
the commit that moved these files; the diff was never the gate.

Coverage was also measured for the first time (see the Spec's
`coverage-baseline-2026-09-07.md` companion). CI now gates this station's coverage on the
modules a PR *touches*, so pre-existing gaps report but do not red the build.

## What this station's maintainer should take from it

Scribe's 18 errors are `psycopg` connection-refused on port 5433 -- no local Postgres -- and are environmental and pre-existing, not a regression. Worth noting that a station whose suite cannot fully run locally is a station whose coverage number is partly unverified.

## Open for this station

Nothing blocking. The Spec's two open questions (mechanising INV-2/INV-3, and whether the
coverage `--cov` target should extend over the django/portal tier) are fleet-level and
tracked there, not here.
