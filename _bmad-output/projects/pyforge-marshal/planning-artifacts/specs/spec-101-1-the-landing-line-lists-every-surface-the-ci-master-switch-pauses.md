---
title: "101.1: The landing line lists every surface the CI master switch pauses"
type: 'fix'
created: '2026-10-14'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-100-1-a-landing-records-which-ci-surfaces-were-paused-when-it-merged.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/landing_ci_pauses.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_landing_ci_pauses.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_steward_internals_import.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - docs/governance/ci-surfaces.yaml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** with the master switch `PAUSE_ALL_CI` on, every job that reads it is skipped, and a dispatch landing's
`ci_pauses_at_merge` will name the master but none of the surfaces it skipped. Story 100.1's Residual risk names this
as its own follow-up ("when steward adds the master's value, a follow-up story lists every surface under it"), and so
does the `spec-pyforge-marshal` memlog's 2026-10-14 decision on CAP-292's open question. Line numbers are at
`22e5c19c28`.

- **Marshal's rule.** `row_counts_as_paused_at_merge` (`core/landing_ci_pauses.py:28`) skips the synthetic
  `unregistered:` and `unregistered-workflow:` rows, lists every `paused-manually` row, skips `opt-in-off` and
  `retired`, and lists any other row whose `live_switch_value`, stripped and lower-cased, is `true`.
  `surfaces_from_envelope` (`:42`) sorts the ids. By CAP-292's design it reads no `verdict`, and it reads no master
  state.
- **Steward's answer.** Steward Story 103.1 (its spec is `ready-for-dev`; its key is `backlog` on `main`) gives
  `steward ci status --json` two things:
  - one row, `master:PAUSE_ALL_CI`, with `declared_state` `live`, `live_switch_value` the variable's value, and
    `verdict` `drift` while it is `true`;
  - one optional boolean row property, `paused_by_master`. It is `true` when the master is `true` and the row is
    gated, whatever the row's verdict. Steward derives "gated" from the workflow files with the CI-surface gate's own
    parser: a `workflow` row when every job's `if:` reads the master, a `ci-job` row when its job's does, a `ci-step`
    row when its step's or its job's does. The master row, the `unregistered:` rows and every `value`, `retired` and
    `paused-manually` row carry `false`.

  A gated row that would otherwise read `live` reads `paused`, and `drift`, `stuck` and `overdue` keep their
  precedence. The verdict enum does not change. On `main` today `data/ci-status-schema.json` has no
  `paused_by_master`.
- **What 100.1 makes of it.** With 103.1 alone, the master row is declared `live` with the value `true`, so 100.1's
  rule lists `master:PAUSE_ALL_CI`. It lists no gated row, because each one's own switch is off. 103.1's own Residual
  risk names this gap as marshal's.
- **The opt-ins.** `docs/governance/ci-surfaces.yaml` declares seven `enable` rows, all `opt-in-off`: six `ci-job`
  rows and one `ci-step` row in `.github/workflows/platform-ci.yml`, in the jobs `build-platform-image`,
  `gke-portability-smoke`, `ocp-portability-smoke`, `air-gap-parity` and `golden-path-promotion`. Each of those jobs'
  `if:` reads `vars.PAUSE_ALL_CI`. So under 103.1 all seven carry `paused_by_master: true` while the master is on,
  whether or not their own opt-in is on. An opt-in that is off would not have run anyway, and its verdict stays
  `opt-in-off`. One that is on (`live_switch_value` `true`) reads `drift` (declared `opt-in-off`, enable switch
  `true`), and it is the master that stops it.

**Approach:**
- **The rule, extended (pure, in `core/landing_ci_pauses.py`).** A row is listed when 100.1's rule lists it, or when
  its `paused_by_master` is the JSON boolean `true` (`is True`) and it is not an opt-in that is off. An opt-in that is
  off is a row whose `declared_state` is `opt-in-off` and whose `live_switch_value`, stripped and lower-cased, is not
  `true`. The `unregistered:`, `unregistered-workflow:` and `retired` skips still run first. A missing or `false`
  `paused_by_master` adds nothing, and so does any value that is not a boolean, the string `"true"` included.
- **Nothing else moves.** Story 100.1 built all of these, and they stay as built: the adapter
  (`adapters/steward_cli.py`), the one read after the check wait, the `unknown` path, `envelope_is_valid`, the
  record's keys (`state`, `surfaces`, `fetched_at`), the PR-body line's format, the outcome and finalize copies and the
  flag `pyforge.marshal.landing_ci_pauses`. The master row stays listed, so the line says the master was on.
- **Steward's real payload.** A marshal test reads steward 103.1's checked-in
  `src/shared/packages/pyforge-steward/tests/fixtures/ci_status_master_on.json` as a file, never by import. Steward's
  own test keeps that file identical to what `run_status` prints, so the marshal rule is checked against the real
  envelope as well as hand-built rows.

**Rejected:**
- **Every `paused_by_master` row.** It names the seven opt-in surfaces while they are off, and they never run unless
  switched on.
- **`verdict == "paused"`.** A gated row that is also `stuck`, `overdue` or `drift` on its own state reads that verdict
  instead, which is CAP-292's reason not to read the verdict. An opt-in that is on reads `drift`.
- **Excluding opt-ins by `verdict == "opt-in-off"`.** A `stuck` opt-in that is off would then be listed. Declared state
  and switch value are what 100.1 already reads.
- **Marshal reads the master and the workflow files.** That makes marshal a second reader of the pause state, against
  CAP-292's constraint. Steward derives gating with the parser the `ci-surface-gates` detector uses.
- **A second key in the record for the master's surfaces.** The master row in `surfaces` already says the master was
  on, and the record stays the one object CAP-292 defines.

Ledger key: `101-1-the-landing-line-lists-every-surface-the-ci-master-switch-pauses`.
Type / Effort / Deps: fix / S / — (a cross-station gate on steward Story 103.1, held as this story's `blocked` ledger
row).

### Living CAP citations

- **`spec-pyforge-marshal` CAP-292** (FR-239; Story 100.1, done): a dispatch landing records which CI surfaces were
  paused when it merged. This story makes the record complete under the master switch, as the Spec's open question
  and the memlog's 2026-10-14 decision foresaw. It mints no CAP and changes no `SPEC.md` text.
- **`pyforge-steward:CAP-166`** (steward Story 99.3, with Story 103.1's master row and `paused_by_master`): the
  envelope this reads. Always cite it qualified; marshal has its own CAP-166.
- **AD-4:** the rule is a pure function in `core/`. **AD-8:** an unread envelope is still `unknown`, never `[]`.
  **AD-71:** the CI estate stays steward's, and marshal reads its CLI's JSON.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag of its own. With
  `pyforge.marshal.landing_ci_pauses` off, no steward call is made, exactly as today.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-14 (the master switch's surfaces at merge)
  entry; Story 100.1's Residual risk; the operator's ask of 2026-10-14, "chain it here".

## Acceptance Criteria

- **AC1 — The master's surfaces are listed.** A unit test feeds `surfaces_from_envelope` an envelope with the master
  `true`, holding these rows:
  - the `master:PAUSE_ALL_CI` row (`declared_state` `live`, `live_switch_value` `"true"`, `verdict` `drift`,
    `paused_by_master` `false`);
  - with `paused_by_master` `true`: two rows declared `live` whose own switch is off, one with the verdict `paused`
    and one with `stuck`; a row declared `paused` whose switch is `"true"`, verdict `overdue`; a row declared `live`
    whose switch is `"true"`, verdict `drift`; and an opt-in declared `opt-in-off` whose switch is `"true"`, verdict
    `drift`.

  The list is every one of those ids, sorted, each once. A parametrized test of `row_counts_as_paused_at_merge` covers
  each row kind alone.
- **AC2 — Not listed.** In the same envelope none of these is listed: an opt-in declared `opt-in-off` whose switch is
  `"false"` or `null`, with `paused_by_master` `true` and verdict `opt-in-off`; a row declared `live` whose own switch
  is off, with `paused_by_master` `false`; a `retired` row with `paused_by_master` `true`; an `unregistered:PAUSE_FOO`
  row with `paused_by_master` `true`; a row declared `live` whose own switch is off and whose `paused_by_master` is the
  string `"true"`, `1` or `null`.
- **AC3 — No field, no change.** No envelope in today's `test_landing_ci_pauses.py` carries `paused_by_master`, and
  each one's record is unchanged. Every existing test in that file passes with no assertion weakened or deleted, the
  flag-off run of Story 100.1's AC7 included.
- **AC4 — The line and the record agree.** Through `execute_dispatch_land`, with the flag on and the steward fake
  returning AC1's envelope, the journal's `ci_pauses_at_merge.surfaces` holds AC1's ids. The body passed to
  `forge.update_pr` ends with one `CI paused at merge:` line naming the same ids in the same order.
- **AC5 — Steward's own payload.** A test reads
  `src/shared/packages/pyforge-steward/tests/fixtures/ci_status_master_on.json` (steward 103.1's AC6 fixture) as a
  file. `envelope_is_valid` is true. `surfaces_from_envelope` contains `master:PAUSE_ALL_CI` and every row whose
  `verdict` is `paused` and whose `paused_by_master` is `true`. It contains no row whose `paused_by_master` is `false`
  unless 100.1's rule alone lists it. The test fails, and never skips, when the file is absent.
- **AC6 — One reader.** `tests/meta/test_no_steward_internals_import.py` passes unedited: no module imports
  `pyforge.steward`, and no module but `adapters/steward_cli.py` invokes steward. No marshal module under `src/` names
  `PAUSE_ALL_CI` or `ci-surfaces.yaml`, or reads a workflow file.
- **AC7 — Mutation.** Each change below fails a named test, and the Auto Run Result records which:
  - ignoring `paused_by_master` (AC1);
  - listing an opt-in that is off (AC2);
  - accepting the string `"true"` for the field (AC2);
  - dropping an opt-in that is on (AC1);
  - listing a gated row by `verdict == "paused"` alone (AC1's `stuck` row).

## Boundaries & Constraints

**Always:**
- Read `paused_by_master` from steward's envelope through Story 100.1's adapter and its one read per landing, as
  100.1 reads every other field.
- Accept only the JSON boolean `true` for the field.
- Keep 100.1's record, its PR-body line and its `unknown` path unchanged for an envelope without the field.
- Reconcile every governed path on the memlogs of the Specs that govern it (`spec-pyforge-marshal`, and
  `spec-pyforge-core`, which co-governs station `src/`), then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never import `pyforge.steward`. Never read `PAUSE_ALL_CI`, `gh`, the Actions API,
  `docs/governance/ci-surfaces.yaml` or a workflow file from marshal, and never decide in marshal which jobs read the
  master.
- Never refuse, delay or re-verdict a landing because of the master, and never wait on CI for it.
- Never add a key to `ci_pauses_at_merge` or change the PR-body line's format; never edit steward or its fixture.
- Never flip `pyforge.steward.ci_pause_control`, `pyforge.marshal.landing_ci_pauses` or `PAUSE_ALL_CI`.

**Residual risk:**
- Under the master the line names every gated surface, which can be most of the registry's 49 pause rows declared
  `live` or `paused`. It stays one line.
- With steward's flag `pyforge.steward.ci_pause_control` off (its default), every landing still records `unknown`, as
  under Story 100.1.
- A steward older than 103.1 sends no `paused_by_master` and no master row, so the record is 100.1's.

## I/O & Edge-Case Matrix

| Row, with the master `true` | `paused_by_master` | Listed |
|---|---|---|
| `master:PAUSE_ALL_CI`, declared `live`, value `"true"`, verdict `drift` | `false` | yes (100.1's rule) |
| declared `live`, own switch off, verdict `paused` | `true` | yes |
| declared `live`, own switch off, verdict `stuck` | `true` | yes |
| declared `paused`, own switch `"true"`, verdict `overdue` | `true` | yes (100.1's rule too) |
| declared `live`, own switch `"true"`, verdict `drift` | `true` | yes (100.1's rule too) |
| declared `opt-in-off`, switch `"true"`, verdict `drift` | `true` | yes |
| declared `opt-in-off`, switch `"false"` or `null`, verdict `opt-in-off` | `true` | no |
| declared `live`, own switch off, verdict `live` (no job, or not every job, reads the master) | `false` | no |
| `paused-manually` | `false` | yes (100.1's rule) |
| `retired` | `true` or `false` | no |
| `value` row (`PLATFORM_CI_REGISTRY`) | `false` | no |
| `unregistered:<NAME>` or `unregistered-workflow:<file>` | any | no |
| any row whose field is `"true"` (a string), `1` or `null` | not the boolean `true` | 100.1's rule only |
| an envelope with no `paused_by_master` (a steward before 103.1) | absent | 100.1's rule only |
| the master unset or `"false"` | `false` on every row | 100.1's rule only |
| steward unreadable | n/a | `unknown`, as under 100.1 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-292 (FR-239), shipped by Story 100.1. No CAP is minted, and no
  `SPEC.md` text changes. Reads `pyforge-steward:CAP-166` as steward Story 103.1 extends it.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-14 (the master switch's surfaces at merge)
  entry.
- Epic: Epic 101 (new), minted with this story, because Epic 100 is `done`. `epic-101` and `epic-101-retrospective`
  are minted with it.
- Ledger key: `101-1-the-landing-line-lists-every-surface-the-ci-master-switch-pauses`.
- Ledger status at mint: `blocked`. It is a cross-station gate on steward Story 103.1
  (`103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses`): the field and the fixture this
  story reads exist only once 103.1 lands. Marshal's `Deps:` parser is station-local, so the gate is this ledger row.
  The operator flips it to `backlog` once 103.1 is `done` on `main` (precedents: marshal 74.2, herald 38.1, doctor
  42.1).
- Deps: — (cross-station, see above).
- Surface: `marshal-policy.toml` `[epic_surfaces]."101"`, added with this mint.
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1–AC6's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_landing_ci_pauses.py src/shared/packages/pyforge-marshal/tests/meta/test_no_steward_internals_import.py -q` — expected: pass.
- `git grep -n -e PAUSE_ALL_CI -e ci-surfaces.yaml -- src/shared/packages/pyforge-marshal/src` — expected: no match, exit 1 (AC6).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- The five mutations of AC7 — expected: each fails its named test. Restore each.
- `git diff origin/main...HEAD --stat` — expected: outside `_bmad-output/` and `scripts/.spec-surface-baseline.json`, only `core/landing_ci_pauses.py` and `tests/unit/test_landing_ci_pauses.py` under `pyforge-marshal`, and nothing under `pyforge-steward`.

## Spec Change Log

- 2026-10-14: minted from the Dream entry of 2026-10-14 (the master switch's surfaces at merge) at the operator's ask
  "chain it here", the follow-up that Story 100.1's Residual risk names. `type: fix`, no flag, no CAP. The key is
  minted `blocked` on steward Story 103.1.

## Review Triage Log

- No review has run yet.
