---
title: '5.1: Retire `provision --runner bmad-loop` in favour of `marshal init`'
type: 'change'
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

**Problem:** one command that provisions a loop home

**Approach:** two stations do not ship two ways to make the same thing, one of them wrapping a legacy script.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-5-1-retire-provision-runner-bmad-loop-in-favour-of-marshal-init.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| an operator runs `steward provision --runner bmad-loop --env <name>` **Then** it either delegates to `marshal init` or exits with a finding naming `marshal ini… | as in epics.md | it either delegates to `marshal init` or exits with a finding naming `marshal init <slug>` as the supported path — never silently provisions via the legacy script | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `--env <name>` (pixi environments, genuinely Steward's) is unaffected | n/a |
| And-clause from epics.md | when the story lands | the removal is recorded in this station's own architecture, not only in Marshal's | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `provision.py`, `cli.py`, `tests/`
Ledger key: `5-1-retire-provision-runner-bmad-loop-in-favour-of-marshal-init`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-5-1-retire-provision-runner-bmad-loop-in-favour-of-marshal-init.md`.

## Epic excerpt

As the operator,
I want one command that provisions a loop home,
So that two stations do not ship two ways to make the same thing, one of them wrapping
a legacy script.

**Type:** change • **Effort:** S • **Deps:** — • **FR/AD:** AD-5 (this station), Marshal marshal:AD-71
**Surface:** `provision.py`, `cli.py`, `tests/`

**Why.** Steward's **own AD-5** already calls this "Marshal-owned machinery", and
`provision --runner bmad-loop` shells to the *legacy* `scripts/bmad-loop-worktree` while
`marshal init` (Epic 1, 10 shipped stories) is a strict superset — worktree plus the
marker↔symlink agreement invariant, the marshal:AD-11 never-write proof, and an idempotent
`done | skipped | failed` step report.

**Acceptance Criteria:**

**Given** an operator runs `steward provision --runner bmad-loop --env <name>`
**Then** it either delegates to `marshal init` or exits with a finding naming
`marshal init <slug>` as the supported path — never silently provisions via the legacy
script
**And** `--env <name>` (pixi environments, genuinely Steward's) is unaffected
**And** the removal is recorded in this station's own architecture, not only in Marshal's

**Status:** done

**Outcome (2026-08-09).** Retired by REPORTING, not delegating. Steward imports nothing
from `pyforge.marshal` and shells to no `marshal` binary; proxying the front door would
create this station's first cross-station coupling and re-wrap the very machinery the
story removes. `run_bmad_loop_worktree` and its stdout parser are **deleted** — a
retirement that leaves the old path importable is a deprecation, not a removal.
`_BMAD_LOOP_WORKTREE_RELATIVE_PATH` survives because `repo_root()` locates the monorepo
by finding that script, which is unrelated to running it. AD-5 amended in **Steward's
own** ARCHITECTURE-SPINE (the AC's explicit requirement), not only in Marshal's chain.
Suite 197 → 198.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `da3f0afb9a` (2026-08-08, "steward 5.1: retire `provision --runner bmad-loop` in favour of `marshal init`"); also `18a5ac49f0` (2026-08-08, "doctor: split Story 5.1 — the source shipped, the wiring did not"); also `bbd4b9f891` (2026-08-07, "herald: Story 5.1 — push regenerated exports with etag guard (CAP-5)"). Ledger row `5-1-retire-provision-runner-bmad-loop-in-favour-of-marshal-init: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py`, `src/shared/packages/pyforge-steward/tests/conformance/test_provision_runner.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
