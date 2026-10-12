---
title: '98.1: Station tests run when what they read changes'
type: 'fix'
created: '2026-10-12'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-2-the-preflight-runs-the-lanes-ci-would-run-for-the-diff-read-from-the-workflow-files.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-97-1-the-not-yet-clean-ceiling-may-shrink-but-never-grow.md
  - .github/workflows/pyforge-station-tests.yml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py
  - src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py
  - src/shared/packages/pyforge-steward/tests/meta/test_lint_types_django_tables.py
  - src/shared/packages/pyforge-core/tests/meta/test_conformance_lane_wired.py
  - src/shared/packages/pyforge-testing-kit/tests/meta/test_testing_kit_lane_wired.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `.github/workflows/pyforge-station-tests.yml` runs each suite only when that suite's own package or a short
shared list moves, but the suites read files far outside both. A change to one of those files runs no suite that reads
it, so a break lands on `main` unseen and reddens the next unrelated PR. `pr-preflight` makes the same choice, because
Story 71.2 runs the workflow's own `changes` shell. Line numbers below are at `5beef7c9eb`.

- **How the workflow chooses today.** `on.pull_request.paths` (:28-:54, and `on.push.paths` :55-:82, identical) lists
  the eight station packages, `pyforge-core`, `pyforge-testing-kit`, `django-pyforge`, `src/platform/config/flags.json`,
  herald's `presentations/**` and `docs-site/**`, atlas's inventory quartet, `pixi.toml`, `pixi.lock`, the container
  inputs and the workflow itself. The `changes` job's filter step (:111-:172) sets `SHARED_CHANGED` from `pyforge-core`,
  `pyforge-testing-kit`, `pixi.toml`, `pixi.lock` and the workflow; each station's output from
  `src/shared/packages/pyforge-<station>` (plus herald's two trees and atlas's `ATLAS_EXTRA`); `core` from the shared
  surface or any station package; `testing_kit` from the shared surface, `django-pyforge` and `flags.json`.
- **What broke.** Herald Story 38.1 (merge `e0b8ceae0c`, 2026-10-11) changed `scripts/lint_types.py` and
  `src/shared/packages/django-herald/**`. Steward's `tests/meta/test_lint_types_django_tables.py` loads
  `scripts/lint_types.py`, reads all nine `django-*/pyproject.toml` and `.github/workflows/lint-types.yml`; CI ran
  `herald-test` and never `steward-test`, and the meta-test went red on `main` (Story 97.1 fixes the test itself).

**Evidence:**
- **The workflow's own rules, run.** The `changes` step's `run:` script, executed as `test_preflight_selection.py`'s
  oracle runs it (event `pull_request`, `GITHUB_BASE_REF=main`, base at `refs/remotes/origin/main`, scratch
  `GITHUB_OUTPUT`), against one-path fixture diffs on 2026-10-12:

  | Changed path | `on.pull_request.paths` fires | Outputs `true` |
  |---|---|---|
  | `scripts/lint_types.py` | no | none |
  | `scripts/target_version_check.py` | no | none |
  | `.github/workflows/lint-types.yml` | no | none |
  | `src/shared/packages/django-herald/src/x.py` | no | none |
  | `src/shared/packages/django-pyforge/src/x.py` | yes | `testing_kit` |
  | `src/platform/config/flags.json` | yes | `testing_kit` |
  | `scripts/fleet_scan.py` | no | none |
  | `scripts/cfe_rebuild_guard_check.py` | no | none |
  | `src/shared/packages/pyforge-steward/src/x.py` | yes | `core`, `steward` |

- **The measured map.** A scope-aware scan of each suite's tests for `Path(__file__)`-anchored reads (`.parents[k]`,
  `.parent`, `/` joins, the names and fixtures bound to them), plus a grep for the portal-package reads the resolver
  misses (`candidate / "src" / "shared" / "packages" / "django-<station>"` loops), tracked paths only. Reads that no
  filter covers today:

  | Job | Outside reads not covered (representative) |
  |---|---|
  | atlas | every `.github/workflows/*.yml` (`test_cap18_kedro_hook_map.py`); `src/platform/config/flags.json`; `django-atlas` (`test_portal_inventory_row.py`); `pyforge-doctor/src` (`test_planning_record.py`); `pyforge-scribe/src` (`test_scribe_plane_recall.py`) |
  | doctor | `.claude/skills/conda-forge-expert/scripts/` (`test_checks_env_hygiene.py`); `.github/workflows/detectors.yml`; `docs/governance/guild-roster.json`; `scripts/{apply_verification_verdicts,coverage_gate,flag_gate_check,fleet_scan,spec_surface_check}.py`; `src/platform/config/`; `django-pyforge/src` (`test_flag_kill_switch.py`); `django-doctor` (`test_portal_fleet_pulse.py`) |
  | herald | `.github/workflows/docsite-check.yml`; `docs/map.yaml`; `docs/foundry/capability-ledger.yaml`; `docsite/` (`build.py`, `README.md`, `assets/fonts/`, `content/dossier.yml`); `django-herald` (`test_portal_herald_guard.py`, `test_portal_deck_status.py`); `pyforge-steward/src` (`test_preflight_pages_lane.py`) |
  | marshal | `_bmad-output/harness-profiles/cursor.toml`; `_bmad/custom/*.toml`; `_bmad/scripts/{bmad_tea_playwright,memlog}.py`; `scripts/{coverage_gate,fleet_picture,promote_sprint_status,spec_surface_check}.py`; `src/platform/compose/compose.yml`; `src/platform/pyproject.toml`; `django-pyforge/src`; `django-marshal` (`test_27_2_portal_loop_homes.py`) |
  | mason | `scripts/cfe_rebuild_guard_check.py`; `django-mason` (`test_portal_last_diagnose.py`); its task's `.claude/skills/conda-forge-expert/tests/meta/test_cli_tool_parity.py` |
  | scribe | `AGENTS.md` (`test_navigation_owner.py`); `src/platform/**/*.py`; `src/platform/db/changelog/changes` (`tests/unit/conftest.py`) |
  | steward | every `.github/workflows/*.yml` (`test_workflow_path_filters_match.py`, `test_preflight_selection.py`); `.github/workflows/lint-types.yml`; `.claude/hooks/session-start.sh` and `.cursor/environment.json` (`test_session_check_entry_points.py`); `scripts/lint_types.py`; `scripts/detectors.py`; `scripts/platform-ci-local.sh`; `src/platform/config/flags.json`; all nine `django-*/pyproject.toml`; `django-pyforge/src`; `django-steward` (`test_first_portal_slice_provision_list.py`); `pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` |
  | warden | `django-warden` (`test_portal_audit_start_get.py`) |
  | core | all of `src/` and `scripts/` (`test_preserve_refs_sole_grammar.py`'s scan roots); `src/platform/config/flags.json` (`test_flags.py`) |
  | testing_kit | none |

  Planning content is read too and is held out by design (Approach): doctor reads every station's deferred-work ledger,
  its own epics and sprint ledger, and `archive/**`; marshal reads every station's `marshal-policy.toml`, story specs and
  `test-architecture.md`; herald reads a steward spec companion; atlas reads `recipes/`.
- **Not a suite read.** `scripts/target_version_check.py` is read by `tests/scripts/test_lint_types_gate.py`, which
  `detectors.yml`'s `pyforge-doctor-scripts-test` runs on every PR; no suite test reads it.
- **The local twin follows.** `preflight_ci` runs the workflow's `changes` job to choose lanes (Story 71.2), so it
  skips what CI skips. `test_preflight_selection.py::test_testing_kit_branch_selects_only_the_kit_not_core_or_stations`
  (:330-:334) asserts that a `django-pyforge` change selects no station suite.
- **Tools.** `actionlint` is in no pixi environment (2026-10-12).

**Approach:** every suite job runs when a tracked path its tests read changes, and a steward meta-test derives those
paths from the tests and proves the workflow fires for each.

- **The workflow.** The `changes` filter step gives each of the ten jobs the inputs its tests read, as literal path
  lists in the shell (one array per job, the way `ATLAS_EXTRA` is written today), and `on.pull_request.paths` and
  `on.push.paths` (identical) fire for every one. The shared surface, herald's two trees and atlas's quartet stay.
  `scripts/lint_types.py`, `scripts/target_version_check.py` (a declared extra: the operator relay names it; no suite
  test reads it), `.github/workflows/lint-types.yml` and every `src/shared/packages/django-*` package fire `steward`;
  each `django-<station>` package fires its station. The `changes` job keeps the shape pyforge-core's
  `test_conformance_lane_wired.py` and the testing kit's `test_testing_kit_lane_wired.py` read: the `SHARED_CHANGED`
  diff list, the `for s in …; do … done` station loop that sets `CORE_CHANGED=true`, the `CORE_CHANGED="$SHARED_CHANGED"`
  seed and the `echo "<job>=…" >> "$GITHUB_OUTPUT"` lines. `core`'s gate follows its measured reads (all of `src/` and
  `scripts/`), and the comment above `core-test` that calls the `django-*` packages "deliberately not `core` inputs" is
  corrected, since `test_preserve_refs_sole_grammar.py` scans them.
- **The meta-test.** `src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py` (new):
  - *Which tests a job runs.* The package's `tests/**/*.py`, plus every outside pytest path the job's pixi task
    collects, read from `pixi.toml` (never copied): atlas's `tests/packaging/test_openteams_handoffs.py` and
    `scripts/tests`, mason's `.claude/skills/conda-forge-expert/tests/meta/test_cli_tool_parity.py`. The jobs and their
    tasks are read from the workflow's `jobs:` and `pixi.toml`, never a hand list; `core` and `testing_kit` are jobs
    like the eight.
  - *What a test reads.* (1) A `Path(__file__)`-anchored expression resolved to a repo path, through `.parents[k]`,
    `.parent`, `.resolve()`, `/` and `joinpath` with string literals, names bound to such expressions in module or
    function scope, and conftest fixtures that return one; a non-literal segment makes the read a glob. (2) A string
    literal, or a `/` chain of literals, of two or more path segments that names a git-tracked file or directory
    (`git ls-files`); a literal that names no tracked path is a fixture name and does not count. Untracked paths
    (`.pixi/`, `.git`, `.steward/`) never count. Reads inside the job's own package are dropped.
  - *Does the workflow fire.* For each distinct read, a tracked representative file (the file, or the first
    `git ls-files` match under a directory or glob) is changed in a fixture repo whose base is
    `refs/remotes/origin/main`; the `changes` step's `run:` script runs as the selection oracle runs it; the job's
    output must be `true`, and `on.pull_request.paths` must match the path under GitHub's glob rules
    (`preflight_ci.filter_matches`). One fixture per distinct representative path, reused across jobs.
  - *Exemptions.* A map of glob to reason, in the test. Its seed holds planning content only:
    `_bmad-output/projects/*/planning-artifacts/**`, `archive/**`, `docs/dreams/**`, `recipes/**`, `.claude/memory/**`
    — Tier 2 planning artifacts, archives, Dreams, the recipe factory and team memory, edited on nearly every chain or
    recipe PR and checked on every PR by `detectors-ci`'s chain detectors; firing doctor, marshal and atlas on all of
    them is the cost this exemption avoids. The live map must stay a subset of the seed (Story 97.1's rule): an entry
    may leave, none may be added.
  - *Its own reads.* The meta-test reads every suite's tests, so steward's list carries
    `src/shared/packages/pyforge-*/tests/**`: a station PR that adds a new outside read runs `steward-test` and is
    caught in that PR.
- **The local twin.** `preflight_ci.py` and `preflight.py` do not change. `test_preflight_selection.py` gains a
  `django-herald`-only branch (selects `pyforge-steward-test` and `pyforge-herald-test`) and a `scripts/lint_types.py`-only
  branch (selects `pyforge-steward-test`); the `django-pyforge` test is rewritten and renamed for the new rule.
- **Rejected:** adding only `scripts/lint_types.py` and the `django-*` packages to steward (closes the reported case,
  leaves the rest of the measured map and the next one unseen); a scanner run inside the CI `changes` job (a scanner bug
  would silently skip suites, where committed lists checked by a test fail loudly); widening every job to every path
  (all ten suites on every PR); hosting the derivation in pyforge-core's tests, where `core-test` already fires on any
  station change (cheaper, but the file would be `spec-pyforge-core`'s chain, not this station's — the alternative if
  `steward-test`'s wider trigger proves too costly).

Ledger key: `98-1-station-tests-run-when-what-they-read-changes`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-159** (the preflight runs the lanes CI's own rules select, read from
  `.github/workflows/*.yml`, never a second list). Story 71.2 built the reader and runs each workflow's `changes` job;
  this story makes those rules complete for the station-tests lane, so CI and `pr-preflight` both run a suite when what
  it reads changes. It changes no behaviour CAP-159 names, so it needs no new CAP and no `SPEC.md` change.
- **Kinship, as Story 71.2 bound them:** `spec-pyforge-core` CAP-8 and CAP-10 (the station-tests lane, `core-test`'s
  gate and the full-ref base) and `spec-pyforge-testing-charter` CAP-3 (`testing-kit-test`'s gate). Their meta-tests
  read this workflow and must stay green; their rules are kept, not rewritten.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag; this one changes which CI jobs run.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-12 (station tests run when what they read
  changes). Authority: the operator's ask "Do this task here: Make steward-test run when lint_types or django pkgs
  change", recorded verbatim in the `spec-pyforge-steward` memlog.

## Acceptance Criteria

- **AC1 — The reported case.** On a one-path fixture diff of `scripts/lint_types.py`, of
  `scripts/target_version_check.py`, of `.github/workflows/lint-types.yml`, and of `pyproject.toml` in each of the nine
  `src/shared/packages/django-*` packages, `on.pull_request.paths` fires and the `changes` script sets `steward=true`.
  A one-path diff in each of `django-atlas`, `-doctor`, `-herald`, `-marshal`, `-mason`, `-scribe`, `-steward` and
  `-warden` also sets that station's output `true`.
- **AC2 — The map is derived, and not blind.** `test_station_tests_trigger_map.py` derives each of the ten jobs' reads
  as the Approach says. The derived map contains at least these rows (non-vacuity; each row a read the job's tests make
  today): steward `scripts/lint_types.py`, `.github/workflows/lint-types.yml`,
  `src/shared/packages/django-herald/pyproject.toml`, `src/shared/packages/django-steward`; herald
  `src/shared/packages/django-herald`, `src/shared/packages/pyforge-steward/src`; atlas `src/platform/config/flags.json`,
  `src/shared/packages/pyforge-scribe/src`; doctor `scripts/fleet_scan.py`, `src/shared/packages/django-pyforge/src`;
  marshal `scripts/fleet_picture.py`; mason `scripts/cfe_rebuild_guard_check.py`; scribe
  `src/platform/db/changelog/changes`; warden `src/shared/packages/django-warden`; core a path under `scripts/`;
  testing_kit `src/platform/config/flags.json`.
- **AC3 — Every derived read fires its job.** For each derived read not exempt, the fixture diff of its representative
  path sets the job's output `true` and matches `on.pull_request.paths`. A failure names the job, the read, the
  representative path and which half failed. On the fixed tree the test passes.
- **AC4 — Exemptions only shrink.** The exemption map is a subset of its five-glob seed, each entry with a reason;
  adding a glob outside the seed fails the test.
- **AC5 — Mutations, each on a scratch copy, never the real workflow.** Each of these fails the meta-test, naming what
  it names: `scripts/lint_types.py` dropped from steward's list (steward, `scripts/lint_types.py`); the
  `django-herald` entry dropped from herald's list (herald); `src/shared/packages/django-*/**` dropped from
  `on.pull_request.paths` (the paths half); an exemption glob added outside the seed. They are committed as tests that
  rewrite a temporary copy of the workflow, as `test_preflight_selection.py`'s `edits` do.
- **AC6 — No job loses a path.** For each trigger the workflow has at `5beef7c9eb` (the shared surface's five paths,
  each station's package, herald's `presentations/` and `docs-site/`, atlas's four quartet inputs, `testing_kit`'s
  `django-pyforge` and `flags.json`, `core`'s station packages), a one-path fixture diff sets at least the outputs it
  set at `5beef7c9eb`. `test_workflow_path_filters_match.py`, pyforge-core's `test_conformance_lane_wired.py` and the
  testing kit's `test_testing_kit_lane_wired.py` pass.
- **AC7 — `pr-preflight` agrees.** In `test_preflight_selection.py`, a `src/shared/packages/django-herald/src/x.py`-only
  branch selects `pyforge-steward-test` and `pyforge-herald-test`; a `scripts/lint_types.py`-only branch selects
  `pyforge-steward-test`; the `django-pyforge` test, renamed to say what it checks, asserts the selection includes `pyforge-testing-kit-test`,
  `pyforge-steward-test`, `pyforge-doctor-test`, `pyforge-marshal-test` and `pyforge-core-test` and equals what the
  parity oracle (`oracle_selection`) selects for the same branch; the parity oracle's fixtures stay green, and each new
  fixture is added to its parametrize list. `preflight_ci.py` and `preflight.py` do
  not change.
- **AC8 — The workflow stays valid.** `yaml.safe_load` parses it; `bash -n` passes on the `changes` step's `run:`
  script; when `actionlint` is on `PATH` it reports nothing for the file (no pixi env carries it today, so this is not
  a gate). The header comment and the `core-test` comment state the rule as built.
- **AC9 — Green, and reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`,
  `pixi run --frozen -e pyforge-core pyforge-core-test`, `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test`
  and `pixi run --frozen -e pyforge-guild lint-types` exit 0. The memlog of every Spec `spec-surface-check` names for a
  changed path gets a surface-reconcile entry naming it and this story, each is stamped scoped (`--spec
  <project>/<spec>`, one each), and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Change only `.github/workflows/pyforge-station-tests.yml`, `src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`
  (new) and `src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py`, plus this story's memlog
  entries and scoped stamps.
- Keep every trigger each job has today (AC6), and keep `on.pull_request.paths` equal to `on.push.paths`.
- Read the job list, the workflow's rules and the pixi tasks from their files at test time; the meta-test holds no
  copy of a station roster or a task command.

**Never:**
- Never change `preflight_ci.py`, `preflight.py`, `coverage-gates.yml`, `pyforge-pip-install.yml` or any other
  workflow; never add `actionlint` or any package to `pixi.toml`.
- Never skip, `xfail` or loosen pyforge-core's or the testing kit's lane meta-tests, or `test_workflow_path_filters_match.py`.
- Never widen a job to `**` or to a whole top-level tree its tests do not read, and never add an exemption to pass a
  read the filter should carry.

**Consequences, recorded:**
- `steward-test` now runs on any PR that edits a station's tests (the meta-test reads them), on any workflow change,
  and on every `django-*` change; `core-test` runs on any `src/` or `scripts/` change; `atlas-test` (Chromium, WASM)
  runs on any workflow change; `scribe-test` (PostgreSQL) runs on an `AGENTS.md` change. The story records the job
  counts its fixtures select for a station-only, a `django-*`-only, a `scripts/`-only and a workflow-only diff.

**Residual risk:**
- The exemption keeps planning content out of every filter: a planning edit that breaks a live-tree test (for example
  a malformed `marshal-policy.toml`, which marshal's tests load) still lands unseen until the next PR that runs that
  suite. Removing the exemption runs doctor and marshal on almost every chain PR; that is the operator's call.
- The derivation is static. A read built from a value it cannot resolve (a path from an environment variable or a
  subprocess) is not derived; the non-vacuity rows (AC2) fail if the derivation goes blind, not if one read slips.

## I/O & Edge-Case Matrix

| Diff | Today (`5beef7c9eb`) | After |
|---|---|---|
| `scripts/lint_types.py` only | no workflow run | `steward` (and `core`) |
| `src/shared/packages/django-herald/**` only | no workflow run | `herald`, `steward` (and `core`) |
| `src/shared/packages/django-pyforge/**` only | `testing_kit` | `testing_kit`, `steward`, `doctor`, `marshal`, `core` |
| `src/platform/config/flags.json` only | `testing_kit` | `testing_kit`, `steward`, `doctor`, `atlas`, `core` |
| `scripts/cfe_rebuild_guard_check.py` only | no workflow run | `mason`, `core` |
| a station's own package | that station, `core` | unchanged, plus every job that reads it (steward's `src` also fires herald; doctor's and scribe's `src` fire atlas) and `steward` when the diff touches `tests/` |
| `pixi.toml` | every job | every job |
| `docs/dreams/*.md` or `_bmad-output/projects/*/planning-artifacts/**` only | no workflow run | no workflow run (exempt) |
| `recipes/<name>/**` only | no workflow run | no workflow run (exempt) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-159, as built by Story 71.2 (lanes read from the workflows). No
  CAP is minted, and no `SPEC.md` text changes. Kinship: `spec-pyforge-core` CAP-8 / CAP-10 and
  `spec-pyforge-testing-charter` CAP-3.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-12 (station tests run when what they read
  changes) entry.
- Epic: Epic 98 (new). Epic 71, which built the reader, is `done`, so the fix opens its own epic. `epic-98` and
  `epic-98-retrospective` are minted with it.
- Ledger key: `98-1-station-tests-run-when-what-they-read-changes`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 97.1 (the ceiling test) is independent; once both land, a station that cleans its portal package
  runs `steward-test` in its own PR and passes it.
- Spec: the `spec-pyforge-steward` memlog records the operator's ask, the evidence, the measured map and the design,
  and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."98"` (added with this mint) covers the station default, which holds
  the meta-test and the preflight test, plus `.github/workflows/pyforge-station-tests.yml` and every Spec memlog.
- Minted 2026-10-12 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). It runs the new meta-test and the preflight selection tests.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py -q` — expected: exit 0 (AC1-AC7).
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: exit 0 (`test_conformance_lane_wired.py`, AC6).
- `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test` — expected: exit 0 (`test_testing_kit_lane_wired.py`, AC6).
- The AC5 mutations, each against a scratch copy of the workflow — expected: each fails naming its job and path; revert each.
- `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/pyforge-station-tests.yml'))"` and `bash -n` on the extracted `changes` script — expected: exit 0 (AC8); `actionlint .github/workflows/pyforge-station-tests.yml` only if it is on `PATH`.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC9).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0; it selects the suites the new rules select for this branch (a workflow change: every job).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-12: minted from the operator's ask "Do this task here: Make steward-test run when lint_types or django pkgs
  change". `type: fix`, no flag, no CAP; bound to `spec-pyforge-steward` CAP-159 through Story 71.2.
