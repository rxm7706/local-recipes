---
title: One generator produces every station's test architecture
type: feature
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: e163eb9216
---

<intent-contract>

## Intent

**Problem:** The eight stations' `test-architecture.md` files still drift and were last fixed by a hand-sweep (FR-129, FR-132); a `TBD` token in output is an undetected failed run.

**Approach:** One automation path (`scripts/bmad_tea_playwright.py` or successor) produces every station's `test-architecture.md`. Regeneration is idempotent on an unchanged tree and produces a changed document when tests moved — its first real run replaces the audit's routed hand-sweep.

## Acceptance Criteria

- One generator produces all 8 stations' `test-architecture.md` files.
- A `TBD` token in output is a failed run (hard fail).
- Idempotent on an unchanged tree; changes when tests moved.
- Fixture-covered for at least one station + fleet smoke or meta check that all eight paths exist without TBD.

## Boundaries & Constraints

**Never:** Implement 19.2 shared kit or 19.3 coverage gates. Never `scripts/bmad-switch`. Finalize marshal ledger only (may write under each station's planning docs as the generator output — that is the story's product).

</intent-contract>

## Code Map

- `scripts/bmad_tea_playwright.py` (or successor) — generator
- All 8 `test-architecture.md` outputs under station planning / docs
- Marshal tests/meta for TBD-fail and idempotence

## Verification

- Generator run green; no TBD tokens
- Idempotent re-run on unchanged tree
- CI: detectors, linter, relevant marshal/meta tests


## Auto Run Result

Status: done
PR: https://github.com/rxm7706/local-recipes/pull/673
Merge SHA: 48423b19b790ff1a068ec882fcbda85f9d0167ad
Tests: `pixi run -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py -q` — 6 passed; CI green on PR #673.
