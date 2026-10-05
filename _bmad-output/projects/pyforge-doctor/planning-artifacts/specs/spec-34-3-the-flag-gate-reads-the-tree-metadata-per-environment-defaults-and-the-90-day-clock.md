---
title: '34.3: The flag gate reads the tree metadata — per-environment defaults and the 90-day clock'
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: '0ad6873d2fa3776d51e20c55ad9b67d345ef9884'
flag-exempt: detector-or-gate   # a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - src/platform/config/flags.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-2's fifth red is a flag still in the tree 90 days after it went ON in
every environment (Q4: the owning station files the removal story). CAP-1's block declares a default per environment
(`production`, `staging`, `dev`), and the Spec's constraint *"Off in production" waits for CAP-5* makes CAP-5 a
prerequisite of that check, not a waiver of it. Today the one tree (`src/platform/config/flags.json`) holds one
`defaultVariant` per flag, no per-environment value and no metadata, so neither check can be computed. Steward Epic 76
lands CAP-5: Story 76.1 the per-environment overlays, Story 76.2 the flagd `metadata` (owner, story key, created date,
ON-everywhere date, cleanup date).

**Approach:** extend `scripts/flag_gate_check.py` (Story 34.2) with the metadata checks, reading the overlay and metadata
shapes exactly as steward 76.1 and 76.2 land them — through `scripts/flag_rule.py`'s one tree reader, never a second:
- FAIL a tree flag whose ON-everywhere date is more than 90 days before the run date, naming the flag, its owner and its
  story key.
- FAIL a tree flag with no owner or no story key in its metadata.
- FAIL a `done` flagged story spec whose declared `default` for an environment disagrees with the tree's value for that
  environment.
- A flag not yet ON in every environment is never red on the clock. The run date is an injectable argument, so the
  boundary (day 90 and day 91) is tested on both sides.
The `--spec` JSON (Story 34.2) carries the per-environment finding for one spec, so marshal's dispatch preflight sees it.

**Blocked until steward Stories 76.1 and 76.2 have landed; the operator flips it.** The ledger key is minted `blocked`
because marshal's `Deps:` parser is station-local, so a cross-station precondition is a ledger gate (AGENTS.md § Known
pitfalls; the doctor 33.1 precedent). Do not start this story while either is unlanded.

Ledger key: `34-3-the-flag-gate-reads-the-tree-metadata-per-environment-defaults-and-the-90-day-clock`.
Ledger status (do not edit the ledger): `backlog` -- flipped 2026-09-30 by the operator after steward Stories 76.1 (`177f67e991`) and 76.2 (`43c7fd0efd`) landed on main.
Type / Effort / Deps: feature / S / S-34.2 (cross-project gate: steward Stories 76.1 and 76.2).

### Living CAP citations

- `spec-feature-flag-governance` CAP-2 (the fifth red) with CAP-5 as its prerequisite (Guild-owned; Doctor as mechanism
  Smith).
- Kinship: steward Stories 76.1 and 76.2 (`spec-feature-flag-governance` CAP-5).

## Acceptance Criteria

- Given a fixture tree whose flag went ON everywhere 91 days before the injected run date When the gate runs Then one FAIL names the flag, its owner and its story key
- Given the same flag ON everywhere 90 days before the run date When the gate runs Then no clock finding
- Given a flag ON in `dev` and `staging` but OFF in `production` When the gate runs Then no clock finding, whatever its age
- Given a tree flag with no owner metadata When the gate runs Then one FAIL names the flag and the missing field
- Given a `done` flagged spec declaring `production: off` and a tree overlay reading ON in production When the gate runs Then one FAIL names the spec, the key and the environment
- Given the same spec at `backlog` When the gate runs Then no per-environment finding
- Given `--spec` on that `done` spec When it runs Then its JSON carries the per-environment finding and `verdict` `red`
- Given the live tree at the landing SHA When `pixi run -e pyforge-guild flag-gate-check` runs Then it exits 0
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Read the overlay and metadata field names from what steward 76.1 and 76.2 landed; never guess a field.
- Keep every change in `scripts/` and `tests/scripts/`; nothing in any `pyforge.<station>` package.
- Keep the one-tree rule (canopy:AD-11): the overlays are views of the one tree, never a second tree.

**Never:**
- Do not start before steward Stories 76.1 and 76.2 have landed; do not flip this story's ledger key.
- Do not write the tree's metadata or remove a flag: the owning station files the removal story (Q4).
- Do not edit `SPEC.md` or `sprint-status-ledger.yaml`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| past the clock | ON everywhere 91 days ago | FAIL naming owner and story | exit 1 |
| on the boundary | ON everywhere 90 days ago | nothing | — |
| not ON everywhere | OFF in production | nothing on the clock | — |
| no owner | metadata lacks `owner` | FAIL | exit 1 |
| per-env mismatch | `done` spec vs overlay | FAIL naming the environment | exit 1 |
| unreadable metadata | malformed overlay | the input named | exit 2 |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-2 and CAP-5 (with the constraint *"Off
in production" waits for CAP-5*) and the Q4 ruling (memlog 23), decomposed 2026-09-28 (night) as Epic 34's mint.

## Spec Change Log

- 2026-09-30 -- operator flip, `blocked` -> `backlog`: the cross-station gate cleared when steward Stories 76.1 (`177f67e991`) and 76.2 (`43c7fd0efd`) landed on main. The tree now carries per-environment values (76.1) and each flag's owner, story, created, ON-everywhere and cleanup dates in flagd metadata (76.2), so every check this story names has something to read. Nothing else in the contract changed. A resumed worktree brings `origin/main` into its branch first (merge, never rebase).

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-2 (Guild-owned; Doctor as mechanism
Smith).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-3-the-flag-gate-reads-the-tree-metadata-per-environment-defaults-and-the-90-day-clock`.
Ledger status at mint: `blocked` (cross-project gate: steward Stories 76.1 and 76.2).
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py -q` — expected: pass.
- `pixi run -e pyforge-guild flag-gate-check` — expected: exit 0 on the landing tree.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Review Triage Log

### 2026-10-05 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - `[false]` `[reject]` No review-layer subagent findings after self-review against the intent contract and verification output.

## Auto Run Result

Status: done

Summary: Extended the flag gate (Story 34.2) with Story 34.3 metadata checks: required tree `metadata.owner`/`metadata.story`, the 90-day clock when a flag is ON in every environment (`--run-date`), and per-environment `flag.default` vs overlay-rendered values for `done` flagged specs. Tree and overlay reads live in `scripts/flag_rule.py` only.

Files changed:
- `scripts/flag_rule.py` — one-tree reader and default comparison helpers
- `scripts/flag_gate_check.py` — three new FAIL kinds and `--run-date`
- `tests/scripts/test_flag_gate_check.py` — AC/matrix coverage and fixture metadata
- Four `done` story specs — reconciled `flag.default` to the live tree/overlays so `flag-gate-check` exits 0

Review: no patches; no deferrals.

Verification: `pytest tests/scripts/test_flag_gate_check.py` 144 passed; `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` 3431 passed; `pixi run -e pyforge-guild flag-gate-check` exit 0; `python scripts/spec_surface_reconcile.py` OK.

Residual risk: future drift between a `done` spec's `flag.default` and steward overlays will red the gate until the owning Smith reconciles the spec.
