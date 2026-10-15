---
title: "103.7: `steward ci status` reads no runs for a retired row, so a landing records the CI pauses"
type: 'fix'
created: '2026-10-15'
status: 'in-progress'
baseline_revision: 'f3cab009ecb460495d4a443423d1bbbb62e46227'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-3-the-operator-sees-the-pause-state-of-every-ci-surface-in-one-command.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-100-1-a-landing-records-which-ci-surfaces-were-paused-when-it-merged.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-39-1-the-dossier-tile-shows-every-ci-surface-that-is-not-live.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/steward_cli.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/landing_ci_pauses.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py
  - docsite/tools/ci_surfaces_tile.py
  - docs/governance/ci-surfaces.yaml
  - docs/how-to/pause-ci.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every dispatch landing records its CI pauses as `unknown`. Marshal 100.1's landing line runs
`pyforge steward ci status --json` and records `{state: unknown}` on exit 1, and that command exits 1 on every run
today. Line numbers are at `f3cab009ec`.

- **The operator's ruling, and its corrected cause.** The ruling of 2026-10-15 read the cause as the three `stuck`
  container-build rows. A `stuck` verdict never fails the read: `run_status` (`ci.py:876`) sets `ok = not partial`,
  and `partial` is only a failed run-list fetch. The three `stuck` rows (`station-tests.guild-container`,
  `platform-ci.container`, `platform-ci.container-dbgpt`) are paused `cost: high` rows whose canary has no green job
  in 15 days; they stay `stuck` after this fix, which is true.
- **The real cause: retired rows.** `_collect_snapshot` (`:229`) runs `gh run list --workflow <file>` for every
  registry row's `workflow`, retired rows included. A failed fetch goes into `run_list_errors`. Measured live at
  `f3cab009ec`, two fetches fail, both `HTTP 404: workflow ... not found on the default branch`:
  - `.github/workflows/reusable-staged-recipes-linter.yml` (`on: workflow_call`);
  - `.github/workflows/reusable-staged-recipes-linter-selftest.yml` (`on: workflow_dispatch` only).

  Both are rows declared `retired` whose files Story 99.7 deleted (`35344ca194`). Neither ever ran as a workflow of
  its own, so GitHub keeps no record for its path. The four other retired rows fetch without error, because GitHub
  keeps a deleted workflow's record once it has run: `linter_issue_comment` and `staged-recipes-linter` read their
  August runs, and `docsite-check` and `docsite-check.check` (the file Story 102.2 folded into `pages.yml`) read a
  last green of `2026-10-15T08:03:18Z` for a file that is no longer in the tree.
- **Why the envelope lands on stderr.** With `partial` true, `run_status` returns `ok=False`, and `cli.main`
  (`:1757`) prints a failed duty's summary on stderr. So `--json` exits 1, with stdout empty.
- **What each consumer does with that today:**
  - Marshal `adapters/steward_cli.py` (`:107`) records `unknown` with reason `"steward ci status partial read (exit
    1): <first stderr line>"` on any exit 1. The doctor 48.1, herald 43.1 and atlas 30.1 landing journals of
    2026-10-15 each hold `"steward ci status partial read (exit 1): {"`.
  - Doctor `sources/ci_pause_drift.py` (`:60`) parses stderr on exit 1, judges the rows, and adds one
    `ci-pause-partial` WARN.
  - Herald's tile reads only the committed snapshot `docsite/content/ci-status.json`, which herald 39.1's spec
    defines as the command's stdout. A partial read leaves an empty stdout to capture.

**Approach:**
- **A retired row's runs are never read.** `_collect_snapshot` collects workflow files only from rows whose `state`
  is not `retired`. `_build_rows` gives a retired row no runs and `last_green_run` `null`, so it can be neither
  partial nor `stuck`. A workflow shared by a retired row and a live one is still read, for the live row. Drift on a
  retired row whose file still exists is judged on the local file, as before.
- **The `unknown` match is exact.** A row reads `last_green_run` `"unknown"` when a run-list error starts with its own
  `"<workflow>: "`, instead of a substring test of the workflow path anywhere in the error.
- **A partial read keeps stdout (the decision).** On a genuine partial read, `--json` still prints its envelope on
  stdout, and the exit stays 1. The envelope carries two optional top-level properties, present only on a partial
  read: `partial: true` and `run_list_errors` (one `"<workflow>: <gh error>"` per failed fetch).
  - **Why.** A partial read lost only run lists. The variables and the workflow states were read in full, so every
    row's `declared_state` and `live_switch_value` are true; only `last_green_run` and the run-based `stuck` rules
    depend on the failed fetches. A reader therefore gets every row it can, and `partial` tells it the rest.
  - **How.** `run_status` asks for stdout with `details["summary_stream"] = "stdout"`, which `cli.main` honours
    beside its existing `details["exit_code"]` request. `ok` stays `False`, so nothing reads a partial read as
    complete. The table form keeps stderr.
  - **Additive.** A complete envelope, the checked-in master-on fixture included, is byte-identical to today's.
- **Consumers, a few lines each (the operator's exception to Epic 103's no-consumer boundary):**
  - Marshal's adapter parses stdout on exit 1. A valid envelope is recorded as a read, and `record_from_envelope` adds
    `partial: true` to the record when the envelope says so. The PR line is unchanged, because the listed surfaces
    come from `declared_state` and `live_switch_value`, which a partial read still holds. Exit 1 with no valid envelope
    on stdout stays `unknown`, and stderr is still never parsed for rows (marshal 100.1's rule).
  - Doctor parses stdout on exit 1, falls back to stderr for an older steward, and keeps its `ci-pause-partial` WARN.
  - Herald's tile changes nothing: `validate_ci_status_envelope` ignores top-level keys it does not know.
- **The how-to.** `docs/how-to/pause-ci.md`'s read path names the exit codes and the partial envelope.

**Rejected:**
- **Treating a 404 for a retired row as not an error.** It still makes a network call for a surface that no longer
  exists, and the four retired rows that do resolve would still report a last green for a deleted file.
- **Exit 0 on a partial read.** Doctor's partial WARN and marshal 100.1's "never treat a partial read as complete"
  both rest on exit 1.
- **`ok=True` with `details["exit_code"] = 1`.** It would print to stdout with no CLI change, but `ok` would then say
  the read succeeded.
- **Always emitting `partial: false`.** It would change every complete envelope and the checked-in master-on fixture
  for no reader's benefit; absence already means a complete read.
- **Dropping the retired rows from the envelope.** Herald's tile lists them, and the registry still declares them.

Ledger key: `103-7-steward-ci-status-reads-no-runs-for-a-retired-row-so-a-landing-records-the-ci-pauses`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-166 (Story 99.3's `steward ci status`, the frozen envelope
  "the one shape the Doctor, Herald and Marshal consumers read"; Story 99.7 retired the rows; Story 103.1 added the
  master row). This story mints no CAP and changes no `SPEC.md`.
- **Governance.** `ci.py`, `cli.py` and `data/ci-status-schema.json` are on `spec-pyforge-steward`'s and
  `spec-pyforge-core`'s surfaces; marshal's adapter and core module on `spec-pyforge-marshal`'s and
  `spec-pyforge-core`'s; doctor's source on `spec-pyforge-doctor`'s and `spec-pyforge-core`'s;
  `docs/how-to/pause-ci.md` on `spec-pyforge-doctor`'s (`scripts/.spec-surface-baseline.json`).
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. `steward ci status` already sits behind
  `pyforge.steward.ci_pause_control`, and marshal's read behind `pyforge.marshal.landing_ci_pauses`.
- **Origin.** Operator ruling 2026-10-15 ("fix this now"), on the `spec-pyforge-steward` memlog with the corrected
  evidence; `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-14 (CI and estate follow-ups) entry's
  2026-10-15 addition.

## Acceptance Criteria

Every steward criterion runs the real `run_status` (or `cli.main`) against a recorded `gh` fixture (the `_make_runner`
pattern in `test_ci_status.py`). None calls GitHub, except AC9's live run.

- **AC1 — A retired row reads no runs.** A registry holding a retired row whose workflow file is absent from the tree,
  with a runner that 404s its run list: `run_status` returns `ok` true, the payload has no `partial` key, the row reads
  `verdict` `retired` and `last_green_run` `null`, and the runner records no `gh run list` for that workflow.
  `cli.main(["ci", "status", "--json"])` exits 0 with the envelope on stdout and nothing on stderr.
- **AC2 — A live row's failed fetch is still partial.** A live row whose run list fails: `run_status` returns `ok`
  false, the payload carries `partial: true` and a `run_list_errors` entry starting with that workflow, the row reads
  `last_green_run` `"unknown"`, and a row of another workflow keeps its own last green.
- **AC3 — A partial read keeps stdout.** For AC2's read, `cli.main(["ci", "status", "--json"])` exits 1 with the
  envelope parseable from stdout and stderr empty; the table form (`ci status` with no `--json`) still prints to stderr.
- **AC4 — The schema stays frozen.** `data/ci-status-schema.json` keeps its `$id`, its required lists and every row
  property, and gains only the optional top-level `partial` (boolean) and `run_list_errors` (array of strings); AC1's
  and AC2's payloads validate. The checked-in `tests/fixtures/ci_status_master_on.json` is unchanged, and every
  existing test in `test_ci_status.py` passes with no assertion weakened.
- **AC5 — Marshal records a read.** `StewardCli.ci_status_record` returns `state` `read` for exit 0 with a valid
  envelope, and for exit 1 with a valid envelope on stdout, the latter with `partial: true`; it returns `unknown` for
  exit 1 with an empty stdout (an envelope on stderr only) and for exit 1 with stdout that is not the envelope. The PR
  line for a partial read names the same surfaces as for a complete one.
- **AC6 — Doctor reads a partial envelope from stdout.** Exit 1 with the envelope on stdout gives its row findings
  plus one `ci-pause-partial` WARN, and exit 1 with the envelope on stderr still does.
- **AC7 — Herald's tile reads it unchanged.** `validate_ci_status_envelope` accepts AC2's partial envelope, and no
  herald or `docsite/` file changes.
- **AC8 — Mutation.** Each change below fails a named test, and the Auto Run Result records which:
  - reading run lists for retired rows again (AC1);
  - dropping the `summary_stream` request, or `cli.main`'s honouring of it (AC3);
  - marshal treating exit 1 as `unknown` whatever stdout holds (AC5).
- **AC9 — The live read.** After the fix, `pixi run --frozen -e pyforge-steward pyforge steward ci status --json` in
  the story worktree exits 0 with the JSON envelope on stdout (a read-only `gh` call; the Auto Run Result records the
  exit code and the row count).
- **AC10 — Green, and the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`,
  `pyforge-steward-coverage-gate`, `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`,
  `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`, `pixi run --frozen -e pyforge-guild lint-types` and
  `flag-gate-check` exit 0. Each changed governed path gets a surface-reconcile entry on the memlog of every Spec that
  governs it, then one scoped stamp per Spec, and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Keep the envelope additive: two optional top-level properties, present only on a partial read; no row property,
  no verdict, no renamed or removed key.
- Keep exit 1 for a partial read, and `ok` false.
- Keep each consumer edit to a few lines, citing this story.
- Reconcile every governed path the change touches on each governing Spec's memlog, then stamp each scoped (AGENTS.md
  pre-PR item 5).

**Never:**
- Never parse stderr for rows in marshal.
- Never write `docs/governance/ci-surfaces.yaml`, a workflow file or a repository variable; never run
  `ci pause|resume --yes` or any `gh` write.
- Never call `gh` in a test.
- Never change herald's tile or `docsite/`.

**Residual risk:**
- A retired row's `last_green_run` reads `null` where `docsite-check` read a last green before; no consumer reads a
  retired row's last green.
- A partial read still exits 1, so a reader that ignores stdout on exit 1 still reports nothing; marshal and doctor
  read it after this story.
- Herald's committed snapshot is the operator's to refresh; it is unaffected until the next refresh, which can now
  capture a partial read too.

## I/O & Edge-Case Matrix

| Situation | Today (`f3cab009ec`) | After |
|---|---|---|
| Retired row, workflow never ran on its own (404) | read partial, exit 1, envelope on stderr | no fetch, `last_green_run` null, exit 0, stdout |
| Retired row, workflow has GitHub history | fetched, last green of a deleted file | no fetch, `last_green_run` null |
| Live row's run list fails | exit 1, envelope on stderr, row `unknown` | exit 1, envelope on stdout with `partial` and `run_list_errors`, row `unknown` |
| Table form, partial | stderr, exit 1 | unchanged |
| Every fetch succeeds | exit 0, stdout | unchanged, byte-identical envelope |
| Marshal, exit 1, envelope on stdout | `unknown` | `read`, `partial: true` |
| Marshal, exit 1, stdout empty | `unknown` | `unknown` |
| Doctor, exit 1, envelope on stdout | `ci-pause-unobserved` | rows judged, `ci-pause-partial` |
| Doctor, exit 1, envelope on stderr | rows judged, `ci-pause-partial` | unchanged |
| `stuck` rows (stale canary) | `stuck`, exit unaffected | unchanged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-166 (Story 99.3's `steward ci status`). No CAP is minted, and no
  `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry, its
  2026-10-15 addition (ci status retired rows).
- Epic: Epic 103 (in progress), which holds the 2026-10-14 `ci status` fixes; Epic 99, which shipped CAP-166, is
  `done`. The epic's no-consumer HARD boundary gains this story's exception, on the operator's ruling.
- Ledger key: `103-7-steward-ci-status-reads-no-runs-for-a-retired-row-so-a-landing-records-the-ci-pauses`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-steward` memlog records the ruling, the corrected evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."103"` gains the marshal and doctor consumer paths.
- Minted 2026-10-15 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding), and it runs `test_ci_status.py`.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py -q` — expected: exit 0 (AC1-AC4).
- `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_landing_ci_pauses.py -q` — expected: exit 0 (AC5).
- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py -q` — expected: exit 0 (AC6).
- The AC8 mutations, one at a time, re-running the named test each time — expected: each fails the named test. Revert each.
- `pixi run --frozen -e pyforge-steward pyforge steward ci status --json` — expected: exit 0, JSON on stdout (AC9).
- `pixi run --frozen -e pyforge-steward pyforge-steward-coverage-gate`, `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`, `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` and `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC10).

## Spec Change Log

- 2026-10-15: minted on the operator's ruling of 2026-10-15 ("fix this now"), with the cause corrected from the
  `stuck` rows to the retired rows' run-list fetches. `type: fix`, no flag, no CAP. Bound to `spec-pyforge-steward`
  CAP-166 through Story 99.3.
