---
title: '56.1: django-debug-toolbar on platform-dev only'
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

**Problem:** `platform-dev` to load `config.settings.local`

**Approach:** mint and `manage.py` do not require a second pixi env.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-56-1-django-debug-toolbar-on-platform-dev-only.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `platform-dev` python cannot import `debug_toolbar` | `django-debug-toolbar` is pinned on the `platform-dev` feature at the same floor as `platform-ci-test` (`>=8.0.0`) | that env imports `debug_toolbar` and can `django.setup()` under `DJANGO_SETTINGS_MODULE=config.settings.local` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `[feature.python-agent-platform]` does not declare the package | n/a |
| And-clause from epics.md | when the story lands | a policy test fails if either pin is wrong | n/a |
| And-clause from epics.md | when the story lands | the proof does not use Docker or CRC | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `pixi.toml` `[feature.platform-dev.dependencies]`;
Ledger key: `56-1-django-debug-toolbar-on-platform-dev-only`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-56-1-django-debug-toolbar-on-platform-dev-only.md`.

## Epic excerpt

As a platform operator,
I want `platform-dev` to load `config.settings.local`,
So that mint and `manage.py` do not require a second pixi env.

**Type:** chore • **Effort:** S • **Deps:** — • **FR/AD:** spec-platform-dev-boots-local
CAP-1
**Surface:** `pixi.toml` `[feature.platform-dev.dependencies]`;
`pixi.lock`; `src/platform/tests/policy/test_platform_dev_local_leaf.py`.
**Given** `platform-dev` python cannot import `debug_toolbar`
**When** `django-debug-toolbar` is pinned on the `platform-dev` feature
at the same floor as `platform-ci-test` (`>=8.0.0`)
**Then** that env imports `debug_toolbar` and can `django.setup()` under
`DJANGO_SETTINGS_MODULE=config.settings.local`
**And** `[feature.python-agent-platform]` does not declare the package
**And** a policy test fails if either pin is wrong
**And** the proof does not use Docker or CRC
**Status:** done

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `56-1-django-debug-toolbar-on-platform-dev-only: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
