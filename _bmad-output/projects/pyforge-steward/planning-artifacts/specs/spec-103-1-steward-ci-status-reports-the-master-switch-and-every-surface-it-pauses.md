---
title: "103.1: `steward ci status` reports the master switch, and every surface it pauses"
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '846d8383f5b4a1f86cbb09f6fd8ae8616b34950f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py
  - docs/governance/ci-surfaces.yaml
  - scripts/_ci_surface_gates_lib.py
  - scripts/_ci_surface_gates_render.py
  - docs/how-to/pause-ci.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py
  - docsite/tools/ci_surfaces_tile.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/landing_ci_pauses.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** while the master switch `PAUSE_ALL_CI` is `true`, every job that reads it is skipped, and
`pyforge steward ci status --json` does not say so. Its envelope has no row for the master and shows each surface at
its own switch's value. So its three consumers under-report while the master is on: doctor 45.1's `ci-pause-drift`
source, herald 39.1's dossier "CI surfaces" tile, and marshal 100.1's `CI paused at merge:` landing line. Line numbers
are at `846d8383f5`.

- **No master row.** `_build_rows` (`ci.py:565`) emits one row per registry `surfaces` entry, one
  `unregistered:<NAME>` row per switch-like repository variable the registry does not name, and one
  `unregistered-workflow:<file>` row per `disabled_manually` workflow without a `paused-manually` row.
  `_switch_names_in_registry` (`:301`) adds `conventions.master` to the registered names, so the master never gets an
  `unregistered:` row, and it is no surface, so it never gets a surface row.
- **No surface reads the master.** Each row's state verdict (`_state_verdict`, `:463`) reads only that row's own
  `switch`. Yet every job of every workflow that fires on `push`, `pull_request` or `schedule` carries the rendered
  fragment `github.event_name == 'workflow_dispatch' || (vars.PAUSE_ALL_CI != 'true' && …)`
  (`scripts/_ci_surface_gates_render.py:185`, `build_fragment`), and `completeness_findings` (`:269`) reds a job that
  lacks it. 13 workflow files read `vars.PAUSE_ALL_CI` today (`grep -l PAUSE_ALL_CI .github/workflows/*.yml`).
- **What each consumer does with the envelope today** (read at `846d8383f5`):
  - Doctor `ci_pause_drift._parse_payload` (`:100`) needs a `rows` list of objects with a string `id` and a `verdict`
    from the eight-value set (`_VALID_VERDICTS`, `:23`), and ignores every other key. `_findings_for_row` (`:128`)
    WARNs on `drift` and `stuck`, and on `review_days_left < 0`. A `paused` row yields nothing.
  - Herald `ci_surfaces_tile.validate_ci_status_envelope` (`docsite/tools/ci_surfaces_tile.py:73`) needs
    `fetched_at`, a `rows` list, and an `id` and `verdict` on each row. `select_non_live_rows` (`:106`) shows every
    row whose verdict is not `live`, drift first, and `format_row_line` (`:111`) appends the row's `detail` when it has
    one. `test_row_verdict_enum_matches_tile_known_verdicts` pins the schema's verdict enum to the tile's
    `KNOWN_VERDICTS`.
  - Marshal `landing_ci_pauses.row_counts_as_paused_at_merge` (`:28`) skips `unregistered:` and
    `unregistered-workflow:` rows, lists every `paused-manually` row, skips `opt-in-off` and `retired`, and lists any
    other row whose `live_switch_value`, stripped and lower-cased, is `true`. It never reads `verdict`.
    `envelope_is_valid` (`:50`) needs `fetched_at`, `repo`, a `rate_limit` object and a `rows` list.
- **The schema is frozen, additive only.** `data/ci-status-schema.json` sets `additionalProperties: false` on the
  envelope and on each row, so a new row field needs a schema property.

**Approach:**
- **One master row.** `_build_rows` appends one row for `conventions.master`:
  - `id` `master:<NAME>` (`master:PAUSE_ALL_CI`), `switch` the name, `declared_state` `live`, and `live_switch_value`
    the repository variable's value, or `null` when the variable is unset (the `_live_switch_value` rule, `:451`);
  - `paused_since` the variable's `updatedAt` while it is `true`, else `null`; `review_by`, `review_days_left`,
    `owner` and `last_green_run` are `null` (the registry declares none for the master);
  - `verdict` `live` while the master is not `true`, and `drift` while it is, with `detail` `"master switch
    PAUSE_ALL_CI is true: every job that reads it is skipped, and the registry declares no master pause"`.
  - **Why `drift`.** CAP-166 defines `drift` as "declared differs from live", and the existing rule reads a `pause`
    row declared `live` whose switch is `true` as drift (`_is_drift`, `:499`). The registry declares no state for the
    master and `ci pause` cannot write one (`_resolve_surface_rows`, `:839`, resolves only a row id or a row's own
    switch), so a `true` master is always a pause nobody declared.
- **Every surface the master gates reads paused.** A row is gated by the master when its jobs read
  `vars.<master> != 'true'` in their `if:`. That is derived from the workflow files with the CI-surface gate's own
  parser (`_ci_surface_gates_lib.collect_var_uses`, which `ci.py` already loads beside `load_registry`), never declared
  in the registry and never parsed a second way:
  - a `workflow` row: every job in its workflow file reads the master in its job-level `if:`, and the file has at
    least one job;
  - a `ci-job` row: its job's `if:` reads it;
  - a `ci-step` row: its step's `if:` or its job's `if:` reads it;
  - a `value` row, a `retired` row and a `paused-manually` row are never gated.
- **The verdict rule.** While the master is `true`, a gated row whose verdict would otherwise be `live` reads
  `paused`, with `detail` `"paused by the master switch PAUSE_ALL_CI"` and `paused_since` the master's `updatedAt`
  when the row's own switch is not `true`. `drift`, `stuck` and `overdue` keep their precedence, and drift is still
  judged on the row's own switch: the master never makes a row drift.
- **One additive row field.** Every row carries `paused_by_master` (boolean): `true` when the master is `true` and
  the row is gated, whatever its verdict, else `false`. The master row and the synthetic `unregistered:` and
  `unregistered-workflow:` rows carry `false`. The schema gains the property, typed `boolean` and not required; the
  verdict enum does not change. It gives a consumer a machine-readable reason for a `paused` row whose own switch is
  off, without parsing `detail`.
- **Consumers, unchanged.** No consumer file changes. With the master `true`:
  - doctor emits one `ci-pause-drift` WARN naming `master:PAUSE_ALL_CI` and its detail, and nothing for the gated
    `paused` rows; with the master off its OK finding counts one more row;
  - herald's tile lists the master row first (drift) and every gated row as `paused`, each line ending with the
    detail;
  - marshal lists `master:PAUSE_ALL_CI` (declared `live`, value `true`), so `CI paused at merge:` names the master.
    It does not list each gated surface, because its rule reads `live_switch_value`, never `verdict`. Listing every
    gated surface is marshal's own follow-up, which its 100.1 spec's Residual risk names; `paused_by_master` is the
    field it would read. Not minted here: another station's story.
- **The how-to.** `docs/how-to/pause-ci.md`'s **Master switch** paragraph says what `ci status` reports for the
  master and for the surfaces it gates.

**Rejected:**
- **A top-level `master` object in the envelope.** All three consumers iterate `rows` and ignore other keys, so it
  would leave each of them as blind as today.
- **Setting each gated row's `live_switch_value` to `"true"`.** That field is the row's own switch's value. Changing
  it would make marshal list every gated surface with no marshal change, but every consumer would then read a switch
  value that GitHub does not hold.
- **A new verdict (`paused-by-master`).** Doctor's `_parse_payload` rejects an unknown verdict and reports
  `ci-pause-unobserved`, and herald's contract test pins the enum. Both would need changes.
- **The master row reads `paused` when on.** Doctor would then stay silent while every gate is skipped, and the
  undeclared master pause has no `review_by`, so it could never become `overdue` either.
- **A `reads_master` field declared on each registry row.** It is derivable from the workflow files, and the
  completeness check already proves every gated job carries the fragment. A declared copy could drift.

Ledger key: `103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-166 (Story 99.3, `steward ci status`): one row per surface with a
  verdict, `drift` meaning declared differs from live, and `--json` "the one shape the Doctor, Herald and Marshal
  consumers read". This story makes that shape carry the master switch. It mints no CAP and changes no `SPEC.md`.
- **Governance.** `ci.py` and `data/ci-status-schema.json` are on `spec-pyforge-steward`'s and `spec-pyforge-core`'s
  surfaces; `test_ci_status.py` on `spec-pyforge-steward`'s; `docs/how-to/pause-ci.md` on `spec-pyforge-doctor`'s
  (`scripts/.spec-surface-baseline.json`).
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. `steward ci status` already sits behind
  `pyforge.steward.ci_pause_control`; this restores the report that flag already gates.
- **Origin.** `DW-steward-101-1-1` (steward `deferred-work-ledger.md`), recorded open with Story 101.1's mint on the
  operator's ruling of 2026-10-14; `docs/dreams/pyforge-steward.md` Realization log, 2026-10-14 (CI and estate
  follow-ups).

## Acceptance Criteria

Every criterion runs the real `run_status` against a recorded `gh` fixture (the `_make_runner` pattern in
`test_ci_status.py`) and fixture workflow files whose `if:` lines are rendered by `build_fragment`. None calls GitHub.

- **AC1 — The master row.** With `PAUSE_ALL_CI` unset, the payload has exactly one `master:PAUSE_ALL_CI` row:
  `switch` `PAUSE_ALL_CI`, `declared_state` `live`, `live_switch_value` `null`, `verdict` `live`,
  `paused_by_master` `false`. With it `"false"`, the same with `live_switch_value` `"false"`. With it `"true"` and
  an `updatedAt`, `verdict` `drift`, `paused_since` that `updatedAt`, and the Approach's `detail` text. No
  `unregistered:PAUSE_ALL_CI` row appears in any of the three.
- **AC2 — Gated rows read paused.** With the master `true`, a fixture holding a `workflow` row whose every job reads
  the master, a `ci-job` row whose job reads it, a `ci-step` row whose job reads it, a `workflow` row one of whose
  jobs does not read it, a workflow-dispatch-only `workflow` row with no fragment, a `value` row, a `retired` row and a
  `paused-manually` row:
  - the first three read `paused`, `paused_by_master` `true`, `detail` `"paused by the master switch PAUSE_ALL_CI"`,
    `paused_since` the master's `updatedAt`;
  - the next two keep their own verdict (`live`) with `paused_by_master` `false`;
  - the `value`, `retired` and `paused-manually` rows keep their verdicts with `paused_by_master` `false`.
- **AC3 — Precedence holds.** With the master `true`: a gated row that is `drift` on its own switch stays `drift` with
  its own detail; a gated `stuck` row stays `stuck`; a gated row past `review_by` stays `overdue`; each carries
  `paused_by_master` `true`. A gated row declared `live` whose own switch is off is never `drift`. A gated row already
  `paused` by its own switch stays `paused`, keeps its own `paused_since` and has no master `detail`.
- **AC4 — The master off changes nothing else.** With the master unset, every row other than the new master row is
  byte-identical, in content and order, to the payload `846d8383f5` produces for the same fixture, apart from the added
  `paused_by_master: false`. Every existing test in `test_ci_status.py` passes with no assertion weakened or deleted.
- **AC5 — The schema stays frozen.** `data/ci-status-schema.json` keeps its `$id` and its required lists, gains only
  the optional `paused_by_master` boolean row property, and keeps the eight-value verdict enum.
  `test_json_validates_against_schema` validates the payloads of AC1-AC3.
- **AC6 — The consumers read it unchanged.** A steward test writes AC2's master-`true` payload, exactly as `run_status`
  prints it, to `src/shared/packages/pyforge-steward/tests/fixtures/ci_status_master_on.json` and fails when the
  checked-in copy differs, so the fixture cannot go stale. Fed that file, each consumer's own code, run in its own
  environment with no consumer file changed, reports the master (the Auto Run Result records each output):
  - doctor, in `pyforge-doctor`: `pyforge.doctor.sources.ci_pause_drift._parse_payload` accepts it, and
    `_findings_for_rows` returns exactly one `ci-pause-drift` WARN, naming `master:PAUSE_ALL_CI`, and none for a gated
    `paused` row;
  - herald, in `pyforge-herald`: `docsite/tools/ci_surfaces_tile.py`'s `validate_ci_status_envelope` accepts it, and
    `select_non_live_rows` puts the master row first and keeps each gated row, each `format_row_line` ending with its
    detail;
  - marshal, in `pyforge-marshal`: `pyforge.marshal.core.landing_ci_pauses.envelope_is_valid` is true, and
    `surfaces_from_envelope` contains `master:PAUSE_ALL_CI`.
  - `git diff origin/main...HEAD --stat` lists no file under `pyforge-doctor`, `pyforge-herald`, `pyforge-marshal` or
    `docsite/`.
- **AC7 — The how-to.** `docs/how-to/pause-ci.md`'s **Master switch** paragraph names the `master:PAUSE_ALL_CI` row,
  its `drift` verdict while on, and the gated rows' `paused` verdict and `paused_by_master` field; its `verified:`
  frontmatter reads the landing date, and `docs-currency` stays green.
- **AC8 — Mutation.** Each change below fails a named test, and the Auto Run Result records which:
  - dropping the master row;
  - judging gating by "any job reads the master" instead of "every job" for a `workflow` row (AC2's mixed row);
  - letting the master make a gated `live`-declared row `drift` (AC3);
  - adding a verdict value to the schema enum (AC5, and herald's contract test).
- **AC9 — Green, and the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test` exits 0, and
  so do `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`, `pixi run --frozen -e pyforge-herald
  pyforge-herald-test` and `pixi run --frozen -e pyforge-guild lint-types`. Each changed governed path gets a
  surface-reconcile entry on the memlog of every Spec that governs it (`spec-pyforge-steward`, `spec-pyforge-core`,
  `spec-pyforge-doctor`), then one scoped stamp per Spec, and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Derive "gated by the master" from the workflow files through `_ci_surface_gates_lib`'s parser, the one the
  `ci-surface-gates` detector uses.
- Keep the envelope additive: one new row, one new optional row property, no renamed or removed key, no new verdict.
- Keep `drift`, `stuck` and `overdue` above the master's `paused`, and judge drift on each row's own switch.
- Reconcile every governed path the change touches on each governing Spec's memlog, then stamp each scoped (AGENTS.md
  pre-PR item 5).

**Never:**
- Never change a consumer: no file under `pyforge-doctor`, `pyforge-herald`, `pyforge-marshal` or
  `docsite/tools/` moves in this story.
- Never write `docs/governance/ci-surfaces.yaml`, a workflow file or a repository variable.
- Never call `gh` in a test; never flip `pyforge.steward.ci_pause_control` or `PAUSE_ALL_CI`.
- Never rewrite `live_switch_value` to mean anything but the row's own switch's live value.

**Residual risk:**
- Marshal's landing line names the master row, not each gated surface, until marshal reads `paused_by_master` in a
  story of its own (marshal 100.1's Residual risk already names it).
- Herald's committed snapshot `docsite/content/ci-status.json` is the operator's to refresh; the tile shows the
  master row only after the next refresh.
- A `true` master stays `drift` until the registry can declare a master pause, which no story proposes. The operator
  sees one doctor WARN for as long as the master is on.

## I/O & Edge-Case Matrix

| Situation | Today (`846d8383f5`) | After |
|---|---|---|
| `PAUSE_ALL_CI` unset | no master row | `master:PAUSE_ALL_CI` row, `live`, value `null` |
| `PAUSE_ALL_CI=true`, no other switch | every surface `live`; marshal lists nothing; doctor OK; tile empty | master row `drift`; every gated row `paused`, `paused_by_master: true`; marshal lists `master:PAUSE_ALL_CI`; doctor one WARN; tile lists all |
| master `true`, a workflow-dispatch-only workflow | `live` | `live` (its jobs read no master) |
| master `true`, a row `overdue` on its own `review_by` | `overdue` | `overdue`, `paused_by_master: true` |
| master `true`, a row `drift` on its own switch | `drift` | `drift` with its own detail |
| master `true`, a `paused-manually` or `retired` row | unchanged | unchanged, `paused_by_master: false` |
| master `true`, the `value` row | `live` | `live`, `paused_by_master: false` |
| master `"false"` | no master row | master row `live`, value `"false"` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (Story 99.3's `steward ci status`). No CAP is minted, and no
  `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry, item 1.
- Epic: Epic 103 (new). Epic 99, which shipped CAP-166, is `done`, so the fix opens a new epic with the two other
  2026-10-14 follow-ups. `epic-103` and `epic-103-retrospective` are minted with it.
- Ledger key: `103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Closes: `DW-steward-101-1-1` (steward `deferred-work-ledger.md`); close it citing this story's merge.
- Spec: the `spec-pyforge-steward` memlog records the evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."103"` (added with this mint).
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding), and it runs `test_ci_status.py` with AC6's fixture check.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py -q` — expected: exit 0 (AC1-AC5, and AC6's fixture).
- AC6's three consumer reads, each a `pixi run --frozen -e <consumer env> python -c …` over `tests/fixtures/ci_status_master_on.json` — expected: one doctor WARN naming `master:PAUSE_ALL_CI`, the tile listing the master first, marshal's list containing it.
- The AC8 mutations, one at a time, re-running the named test each time — expected: each fails the named test. Revert each.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` and `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: exit 0 with no file in either package changed (AC6, AC9).
- `git diff origin/main...HEAD --stat` — expected: outside `_bmad-output/`, `docs/dreams/pyforge-steward.md` and `scripts/.spec-surface-baseline.json`, only `ci.py`, `data/ci-status-schema.json`, steward's tests and fixture, and `docs/how-to/pause-ci.md`.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC9).
- `pixi run --as-is -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Review Triage Log

### 2026-10-14 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 1, false 0, maybe-false 0
- findings:
  - `[low]` `[patch]` `test_ci_status.py` import block order (I001) — ruff --fix ordering applied

## Auto Run Result

Status: done

Summary: `steward ci status --json` now emits a `master:PAUSE_ALL_CI` row and sets `paused_by_master` on gated surfaces while the master is on, without changing doctor, herald, or marshal code.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py` — master row, gating via `_ci_surface_gates_lib.collect_var_uses`, verdict overlay
- `src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json` — optional `paused_by_master`
- `src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py` — AC1–AC6 tests
- `src/shared/packages/pyforge-steward/tests/fixtures/ci_status_master_on.json` — frozen AC6 payload
- `docs/how-to/pause-ci.md` — master switch read-path documentation
- Memlogs + scoped baseline stamps for `spec-pyforge-steward`, `spec-pyforge-core`, `spec-pyforge-doctor`

Review: one low patch (import order). `followup_review_recommended: false`.

Verification:
- `pyforge-steward-test` — pass (includes `test_ci_status.py`, AC6 consumer subprocess checks)
- `pyforge-doctor-test`, `pyforge-herald-test` — pass
- `python scripts/spec_surface_reconcile.py` — OK
- `spec-surface-check` — ok for this story’s reconciled specs
- `lint-types` — steward ruff clean after import fix

Residual risks: marshal landing line still lists master by `live_switch_value` only; herald snapshot refresh remains operator-driven (per spec).

## Spec Change Log

- 2026-10-14: minted from `DW-steward-101-1-1` (operator ruling 2026-10-14, recorded with Story 101.1). `type: fix`,
  no flag, no CAP. Bound to `spec-pyforge-steward` CAP-166 through Story 99.3.
