---
title: '57.1: One frozen env replaces the pip `--no-deps` layer'
type: 'chore'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the platform image produced from a single `pixi install --frozen -e python-agent-platform` whose lock already carries the Django-host extras

**Approach:** a conda/pip overlap (the `mcp` package uninstall CRC hit 2026-08-25) fails at lock time, never as a silent Containerfile uninstall.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-57-1-one-frozen-env-replaces-the-pip-no-deps-layer.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| the extras lived in `[feature.platform-image-pip]` behind a `pip install --no-deps` Containerfile RUN | this story lands **Then** those extras (`django-structlog`, `uvicorn-worker`, etc.) are pinned on `[feature.python-agen… | those extras (`django-structlog`, `uvicorn-worker`, etc.) are pinned on `[feature.python-agent-platform.dependencies]` directly from conda-forge | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the image interpreter imports them with no pip layer RUN | n/a |
| And-clause from epics.md | when the story lands | `platform-ci-test` stays its own separate conda solve (psycopg3 vs image psycopg2) | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `57-1-one-frozen-env-replaces-the-pip-no-deps-layer`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-57-1-one-frozen-env-replaces-the-pip-no-deps-layer.md`.

## Epic excerpt

As a platform operator,
I want the platform image produced from a single `pixi install --frozen -e
python-agent-platform` whose lock already carries the Django-host extras,
So that a conda/pip overlap (the `mcp` package uninstall CRC hit 2026-08-25)
fails at lock time, never as a silent Containerfile uninstall.

**Type:** chore • **Effort:** M • **Deps:** — • **FR/AD:** spec-platform-image-one-pixi-env CAP-1
**Given** the extras lived in `[feature.platform-image-pip]` behind a `pip
install --no-deps` Containerfile RUN
**When** this story lands **Then** those extras (`django-structlog`,
`uvicorn-worker`, etc.) are pinned on `[feature.python-agent-platform.dependencies]`
directly from conda-forge
**And** the image interpreter imports them with no pip layer RUN
**And** `platform-ci-test` stays its own separate conda solve (psycopg3 vs image psycopg2)
**Status:** done — shipped `59083b8391` (2026-08-25); re-verified live
2026-09-11 (`import django_structlog` succeeds, no pip layer)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `57-1-one-frozen-env-replaces-the-pip-no-deps-layer: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
