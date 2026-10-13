---
title: '99.4: The operator pauses and resumes a CI surface through one journaled path'
type: 'feature'
created: '2026-10-13'
status: 'ready-for-dev'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
flag:
  key: pyforge.steward.ci_pause_control       # Story 99.3's (one flag per CAP)
  provider: openfeature-file                  # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # Story 99.3's values
  scope: global                               # v1 is global only
  fallback: the ci pause and ci resume verbs refuse naming the flag; no variable is written
  cleanup: with Story 99.3's flag, 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command.md
  - docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md
  - docs/governance/ci-surfaces.yaml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The two live pauses were set by hand in the GitHub UI with no reason, owner or review date on record,
and nothing stops a third from being set the same way (`docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 4.5).

**Approach:** Two write verbs on Story 99.3's `ci` duty: `steward ci pause` and `steward ci resume`. Each is a dry
run unless `--yes` is given; `--yes` is the operator's (CAP-166's constraint: agents read).

- **`ci pause <surface|switch> --reason "…" --review-by <YYYY-MM-DD>`.** Resolves the registry row by `id` or by
  switch name; refuses before any write on a `retired` row, a `gate: true` row without
  `--i-am-removing-a-merge-gate` (ruling Q5), a `review_by` in the past, or an empty reason. Without `--yes` it
  prints the `gh variable set <SWITCH> --body true --repo rxm7706/local-recipes` argv, the registry diff (`state:
  paused`, `paused_since: <today>`, `paused_by: <git config user.name>`, `reason`, `review_by`), and the
  `scribe capture --type project` text, and makes no `gh` call and no write. With `--yes` it runs the `gh` call,
  writes the row in the current checkout and says the change lands through a PR, appends one JSON line to
  `.steward/ci-pauses.log` (`{ts, action, switch, surface, reason, review_by, by}`), and runs
  `pixi run -e pyforge-guild scribe capture --type project --text "…"`.
- **`ci resume <surface|switch>`.** The inverse: `gh variable delete <SWITCH> --repo rxm7706/local-recipes` (an unset
  variable reads `''`), the row back to `live` (or `opt-in-off` for an `enable` switch), the journal line, the
  capture. Same dry-run default and the same refusals.
- **Order of a `--yes` run.** Refusals, then `gh`, then the registry write, then the journal, then the capture; a
  `gh` failure stops before any file write and exits with the documented code (AD-8).

Ledger key: `99-4-the-operator-pauses-and-resumes-a-ci-surface-through-one-journaled-path`.
Type / Effort / Deps: feature / S / S-99.3.

### Living CAP citations

- **`spec-pyforge-steward` CAP-166** (FR-39): the one write path; its constraint "pauses are written by the operator,
  through one path".
- **AD-1** (`gh` and `scribe` by subprocess), **AD-7**, **AD-8**.
- **Flag:** Story 99.3's `pyforge.steward.ci_pause_control`.
- **Origin.** The 2026-10-12 Dream entry; rulings Q5 and Q8.

## Acceptance Criteria

- **AC1 — Dry run.** Without `--yes`, `ci pause guild-container --reason r --review-by 2026-11-01` prints the argv,
  the diff and the capture text; a fake subprocess records no `gh` call and the registry file is byte-identical.
- **AC2 — `--yes`.** With `--yes`, the fake records `gh variable set PAUSE_CONTAINER_BUILDS --body true --repo
  rxm7706/local-recipes`, the registry row equals the printed diff, `.steward/ci-pauses.log` gains one line, and the
  capture argv is recorded.
- **AC3 — Refusals.** A `gate: true` row without `--i-am-removing-a-merge-gate`, a `retired` row, a past
  `review_by` and an empty reason each refuse before any call or write.
- **AC4 — Resume.** `ci resume` records `gh variable delete …`, sets the row back, journals and captures.
- **AC5 — `gh` failure.** A failing `gh variable set` leaves the registry and the journal untouched and exits with
  the documented code.
- **AC6 — Nothing live.** No test calls a live `gh` or `scribe`.

## Boundaries & Constraints

- No story test or verify command runs a live `--yes`; the operator pauses and resumes.
- The duty writes the registry in the current checkout only; it never commits or pushes.
- The GitHub UI's disable-workflow button stays outside the path; Story 99.3's `drift` verdict reports it.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `ci pause PAUSE_CONTAINER_BUILDS` (by switch) | resolves the `guild-container` row |
| a switch shared by two rows (`PAUSE_PLATFORM_CONTAINER_BUILDS`) | both rows written, one `gh` call, one journal line naming both |
| `ci pause` on an already `paused` row | refusal naming the existing `paused_since` and `review_by` |
| `ci resume` on a `live` row | refusal, nothing to resume |
| an `enable` switch (`PLATFORM_CI_AIR_GAP_PARITY`) | `pause` refuses (it is an opt-in); `resume` is not offered |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (FR-39), minted 2026-10-12.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (ci pause control plane) entry.
- Epic: Epic 99, Stories 99.1–99.7.
- Ledger key: `99-4-the-operator-pauses-and-resumes-a-ci-surface-through-one-journaled-path`.
- Ledger status at mint: `backlog`.
- Deps: S-99.3. `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`.
- Specced 2026-10-13 from the epic's text ahead of its dependencies' landing; the implementing session reads the
  landed `ci` duty first and extends it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_ci_pause.py -q` — expected: pass (AC1–AC6).
- `pixi run --frozen -e pyforge-guild detectors-ci` and `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: specced from Epic 99's Story 99.4 text ahead of its dependencies' landing so the steward chain runs
  unattended (operator direction 2026-10-13).
