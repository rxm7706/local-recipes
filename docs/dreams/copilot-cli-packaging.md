---
title: copilot-cli on conda-forge — blocked at the license
type: dream
owner: mason
status: archived
archived-reason: blocked
---

# copilot-cli on conda-forge

## The Dream

Package GitHub's **Copilot CLI** for conda-forge so the agent tooling the
factory itself leans on could be installed the same way everything else is.

## Why it was archived

**Blocked, and not by anything we can fix.** `LICENSE.md` §2 forbids standalone
redistribution — precisely what a conda package is. staged-recipes **#32522** was
rejected on that clause. No recipe change resolves it; only an upstream
relicense would, and that is not ours to make.

`recipes/copilot-cli/` remains on disk as a **local-only** recipe: it builds and
installs here, and it must never be submitted. The archive entry exists so the
next person to notice the directory does not re-litigate a settled rejection.

## Kinships

[[packaging-factory]] (the practice) · [[enterprise-airgap]] (the class of
license constraint that decides what may be mirrored at all).

## Realization log

- **2026** — staged-recipes #32522 rejected on the LICENSE.md §2 clause.
- **2026-07-25** — **ARCHIVED (blocked)** during the Dream-lifecycle
  reconciliation; formerly a hardcoded console entry with no Dream file behind it.
