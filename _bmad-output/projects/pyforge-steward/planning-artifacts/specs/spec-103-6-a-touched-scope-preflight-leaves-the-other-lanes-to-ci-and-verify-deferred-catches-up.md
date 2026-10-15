---
title: "103.6: A touched-scope preflight leaves the other lanes to CI, and `verify-deferred` catches up"
type: 'feature'
created: '2026-10-15'
status: 'in-review'
baseline_revision: 'fccf4f3ee78b1d7280bfe8101617d75afc579447'
flag:
  key: pyforge.steward.preflight_ci_arbitrates    # new; minted by this story
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through Epic 76's overlay (src/platform/config/flag-overlays.json)
  scope: global                                   # v1 is global only
  fallback: 'pr-preflight runs every lane the diff selects, as today (scope full); PYFORGE_PREFLIGHT_SCOPE=touched still asks for the touched scope for one run; verify-deferred is not gated, since it only reads the journals and runs the full preflight'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-1-every-preflight-run-journals-each-lane-s-wall-time-and-exit-code.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-2-the-preflight-runs-the-lanes-ci-would-run-for-the-diff-read-from-the-workflow-files.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-99-5-the-preflight-honors-what-ci-will-skip-and-says-so.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-5-the-preflight-keys-each-lane-by-its-task-and-its-environment.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_budget.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - scripts/pre_push_preflight.sh
  - pixi.toml
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - docs/governance/flag-inventory/pyforge-steward.md
  - AGENTS.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every push waits on the whole local twin of CI. `pixi run -e pyforge-guild pr-preflight` (CAP-159, run by
CAP-154's pre-push hook) runs every lane CI's own workflow rules select for the diff (Story 71.2), and a shared-surface
change selects all of them. Line numbers are at `fccf4f3ee7`.

- **What it costs.** Measured 2026-10-14/15: the local lanes run in parallel and finish in about 10 min on a quiet
  host. Under host load 29–114 they took 13–28 min and timed out: `chain_currency_sweep_check` passed its 300 s limit
  though it takes 75 s alone, and atlas's e2e port binds passed their 60 s limit. The slowest lanes were
  `pyforge-steward-test` and the steward coverage gate (9.7–17.9 min each), `test-ci` (13–28 min) and `detectors-ci`
  (6–11 min). GitHub runs the same lanes in about 10 min.
- **The only way out is all or nothing.** `PYFORGE_PREFLIGHT_SKIP=1` (`scripts/pre_push_preflight.sh`, checked before
  the hook calls pixi) skips every lane and journals one line to `.steward/preflight-skips.log`. Nothing lists what a
  run of such pushes left unverified, or verifies it later.
- **The cheap catchers are already separate.** `spec-surface-check`, `flag-gate-check`, `story-status-check`,
  `ledger-regression-check` and `chain-completeness-check` are guild tasks of their own (`pixi.toml`, each a `cmd`
  under `[feature.guild-tasks.tasks]`) and parts of `detectors-ci`. At `f7be77efad` in `pyforge-guild` they took
  2.9 s, 2.4 s, 0.6 s, 0.9 s and 0.7 s. `detectors.yml` has no `paths` filter, so `detectors-ci` is selected for every
  diff.
- **Where a run is decided.** `run_preflight` (`preflight.py:764`) selects (`:797`), drops CI-paused lanes (`:800`-
  `:834`), prints the count (`:835`-`:841`) and journals one record per run (`:1103`-`:1132`, and the interrupted
  record at `:1053`-`:1069`). `main` (`:1166`) parses `--jobs`, `--keep-going` and `--ignore-ci-pauses`. The only
  reader of the journal is `preflight_budget`, which ignores keys it does not know.
- **The operator's rulings, 2026-10-15** (verbatim in the `spec-pyforge-steward` memlog): turn off what a push can
  leave to CI and verify everything at the end; make it a flag and an environment variable; chain it now for speed
  to market before wave 2.

**Approach:** a second scope for one preflight run, `touched`, chosen per run and defaulted by a flag.

- **The scope.** `PYFORGE_PREFLIGHT_SCOPE` set to `full` or `touched` chooses it. Unset, the flag
  `pyforge.steward.preflight_ci_arbitrates` chooses it: on means `touched`, off means `full`. Any other value,
  including the empty string, refuses with exit 2 and names the two values; it never falls back. The flag is read only
  when the variable is unset. A flag-tree error (a bad `PYFORGE_ENVIRONMENT`) refuses with exit 2 too. The scope is
  resolved in `main`, so `run_preflight` keeps `full` as its default and its callers keep their behaviour.
- **The touched cut.** It starts from the lanes `full` would run: the selection, after the CI pause filter. It keeps
  a lane when one of these holds, and records why:
  - *its station package changed:* the lane's environment is `pyforge-<x>` and the diff changes a path under
    `src/shared/packages/pyforge-<x>/` or `src/shared/packages/django-<x>/` (each only if the directory exists);
  - *a path its command names changed:* a token of the lane's pixi `cmd`, read relative to the task's `cwd` when it
    has one, names an existing file or directory in the repository (never the root itself), and a changed path is
    that path or lies under it;
  - *lint and types:* the lane's task is in the `depends-on` closure of the `lint-types` task and the diff changes a
    `.py` or `.pyi` file under `src/`.

  Lanes are keyed by `(task, environment)`, as Story 103.5 made them. A kept lane brings the lanes it depends on. When
  `detectors-ci` is among the lanes and is not kept, the five fast-core tasks run in its place, in its environment
  and its position. A fast-core task missing from `pixi.toml`, or without a `cmd`, is a config error (exit 2). Every
  other lane is **deferred**, with the reason `CI arbitrates`. The changed paths are the selection's own: the diff
  against `refs/remotes/origin/main` and the working tree's staged, unstaged and untracked paths. When the selection
  could not read the diff (`all_reason`), the cut keeps every lane and says so on stdout.
- **What the run says.** Its stdout names the scope and where it came from (the variable, or the flag's value), and
  one line per deferred lane, `<task>@<environment>`. The stderr count line keeps its meaning and adds the deferred
  count.
- **The journal, additively.** The run record (and the interrupted record) gains `mode` (`full` or `touched`) and
  `deferred` (a list of `{lane, environment, reason}`, empty in `full`). No key is renamed and none changes its
  meaning. `selection.mode` (`diff` or `all`) is a different key and stays as it is. A record without `mode` reads as
  `full` with nothing deferred.
- **The skip keeps its precedence.** The hook already checks `PYFORGE_PREFLIGHT_SKIP=1` before it calls pixi, so a
  skipped push reads no scope; a push that runs passes the variable through the hook's environment. The hook does not
  change.
- **The catch-up: `pyforge steward preflight verify-deferred [--since YYYY-MM-DD]`.** A new duty, `preflight`, with
  one verb (a duty must have a verb, as `ci` does). It reads `.steward/preflight-runs.jsonl` and
  `.steward/preflight-skips.log` under the repository root, and prints on stdout every run record since the date
  (UTC, inclusive; every record when `--since` is absent) whose `deferred` is not empty, and every skip line since the
  date, except branch deletes, which push no commits. Each line has the time, branch or refs, head, lanes (the
  deferred `task@environment` list, or `every lane`) and why. Malformed lines are skipped with a warning on stderr.
  Then it runs `pixi run --frozen -e pyforge-guild pr-preflight` from the repository root, with
  `PYFORGE_PREFLIGHT_SCOPE=full` and git's hook variables unset, as the hook does. It reaches pixi by subprocess
  (AD-1) and returns a `DutyResult` (AD-8). Exit codes: 0 when the full preflight is green, 1 when it is red, 2 for a
  bad `--since` (argparse), 3 when the preflight could not run (its exit 2, or no `pixi` on `PATH`), and 130 when it
  is interrupted.
- **The flag is registered everywhere a flag is.** In `src/platform/config/flags.json`, with metadata owner
  `steward`, this story's key and `created: 2026-10-15`, `defaultVariant` `off`. In
  `src/platform/config/flag-overlays.json`, on in `dev` and off in `staging` and `production`. In
  `src/shared/packages/pyforge-core/tests/unit/test_flags.py` (`_SHIPPED_CLOCKS` and the per-environment table) and
  `src/platform/tests/test_openfeature_file_flags.py` (`_SHIPPED_BOOLEANS`). In
  `docs/governance/flag-inventory/pyforge-steward.md`, regenerated with `flag-inventory`. The key is read in
  `preflight.py`, so it is never an orphan.
- **Docs.** `AGENTS.md` § *Running and verifying* names the flag, the variable and `verify-deferred` where it names
  `PYFORGE_PREFLIGHT_SKIP=1` as the opt-out.

**Rejected:**
- **A `--scope` flag on `pr-preflight`.** The hook calls `pr-preflight` with no arguments and must not change; an
  environment variable passes through it as it is.
- **Reading the scope inside `run_preflight`.** With the flag on in dev, every test and caller of `run_preflight`
  would change scope with it. `main` reads it once, and `run_preflight` takes it as a parameter.
- **Running the fast core always.** `detectors.yml` fires on every pull request today, so the result is the same, but
  tying the fast core to `detectors-ci` keeps the touched scope a subset of what CI runs.
- **A hand-written lane-to-path table.** The cut reads each lane's paths from its own pixi `cmd` and each station's
  from its environment's name, so a new lane needs no second registration.
- **Counting the task's `cwd` as a path it names.** `docs-site-install` (`npm ci`, `cwd = "docs-site"`) would then run
  for every change under `docs-site/`, without the lanes that depend on it.
- **Deferring with the hook's skip journal.** The skip log records pushes, not lanes; the deferred lanes belong to
  the run record, beside the lanes that ran.
- **Gating `verify-deferred` behind the flag.** It must still list, and verify, the runs deferred while the flag was
  on after the flag goes off.

Ledger key: `103-6-a-touched-scope-preflight-leaves-the-other-lanes-to-ci-and-verify-deferred-catches-up`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (Stories 71.1-71.3, 71.6, 71.7, 71.8, 71.10, 99.5, 103.5): the
  lane list read from `pixi.toml`, the lanes CI's rules select, concurrent lanes, the journal and the budget check
  that reads it. This story adds a second scope to the same runner and a duty that reads its journal. It mints no CAP
  and changes no `SPEC.md`. CAP-154 (the pre-push hook) is unchanged.
- **Governance.** The steward modules and tests are on `spec-pyforge-steward`'s surface, and `spec-pyforge-core`
  co-governs every station's `src/`; the core flag test is on `spec-pyforge-core`'s; the flag tree, the overlay and
  the platform test are on the platform's and the flag governance Spec's (`scripts/.spec-surface-baseline.json`).
- **The flag.** Under `spec-feature-flag-governance` CAP-2 a `type: feature` story carries a `flag:` block; CAP-4's
  gate clause wants a test that runs the key in both states.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-14 (CI and estate follow-ups) entry, its
  2026-10-15 addition (CI arbitrates the deferred lanes).

## Acceptance Criteria

Every criterion runs the real module function (`resolve_scope`, the cut, `run_preflight`, `main`, the duty) on
fixture `pixi.toml` files, fixture repositories and injected lane runners. None runs pixi.

- **AC1 — The scope resolves.** With `PYFORGE_PREFLIGHT_SCOPE` unset, flag on gives `touched` and flag off gives
  `full`, each naming the flag as its source (a `flag_states` test). `full` and `touched` give themselves whatever the
  flag reads, and the flag is not read. Any other value (`bogus`, `Touched`, the empty string) raises the scope error,
  and `main` exits 2 with a message naming `full` and `touched`, starting no lane.
- **AC2 — The skip comes first.** The hook, run in a throwaway repository with a fake `pixi` on `PATH`, exits 0 with
  `PYFORGE_PREFLIGHT_SKIP=1` and `PYFORGE_PREFLIGHT_SCOPE=bogus`, never calls pixi, and journals the skip. Without the
  skip, the fake pixi sees the variable's value.
- **AC3 — The cut.** On a fixture with lanes for two stations, a lint lane, a lane whose command names a path,
  `detectors-ci` and one lane depending on another:
  - a diff under `src/shared/packages/pyforge-a/` keeps `pyforge-a`'s lanes and defers `pyforge-b`'s;
  - a diff to the path a lane's command names keeps that lane and the lanes it depends on;
  - a `.py` diff under `src/` keeps the lint lanes, and a `.md` diff under `src/` does not;
  - `detectors-ci` is deferred and the five fast-core lanes run in its environment and its place;
  - a diff that touches nothing keeps only the fast core;
  - an unreadable diff keeps every lane, defers none, and says so;
  - a fast-core task missing from `pixi.toml` is a config error.
- **AC4 — The run and the journal.** `run_preflight(scope="touched")` runs exactly the kept lanes; its record carries
  `mode: touched` and `deferred` with each lane's `lane`, `environment` and `reason: CI arbitrates`; its stdout names
  the scope, its source and each deferred lane. `run_preflight()` journals `mode: full` and `deferred: []` and runs
  what it ran before. The interrupted record carries both keys too. Every key the record had before keeps its value.
- **AC5 — Old records still parse.** `preflight_budget` judges a journal holding a record without `mode` and one
  with it, as before.
- **AC6 — `verify-deferred` lists.** Given a journal with a `full` run, a `touched` run with two deferred lanes, a
  `touched` run before `--since`, a malformed line, and a skip log with a manual skip, a `dispatch/*` skip and a
  branch delete, it prints the deferred run (time, branch, head, both `task@environment` lanes) and the two skips
  (refs, sha, `every lane`, reason), and nothing else; without `--since` it prints the earlier run too.
- **AC7 — `verify-deferred` verifies.** It runs `pixi run --frozen -e pyforge-guild pr-preflight` once from the
  repository root with `PYFORGE_PREFLIGHT_SCOPE=full`, and the duty exits 0, 1, 3 and 130 when that exits 0, 1, 2 and
  130; 3 when `pixi` is missing; 2 for `--since 2026-13-01` or `--since yesterday`, running nothing. `steward
  preflight` with no verb is a usage error.
- **AC8 — The CLI.** `preflight` is the thirtieth duty: `test_cli.py`, `test_restore_duty.py` and `test_estate.py`
  count 30, and `test_duty_protocol.py` resolves it to a conforming duty.
- **AC9 — The flag.** The key is in the tree with its five metadata fields (owner `steward`, the story key, created
  `2026-10-15`, two empty clocks), `defaultVariant` `off`, overlays on in dev and off in staging and production; the
  core and platform flag contract tests list it; `flag-inventory` lists it on CAP-159; `flag-gate-check` exits 0.
- **AC10 — Docs.** `AGENTS.md` § *Running and verifying* names `pyforge.steward.preflight_ci_arbitrates`,
  `PYFORGE_PREFLIGHT_SCOPE` and `verify-deferred` beside `PYFORGE_PREFLIGHT_SKIP=1`; `governance-currency` exits 0 and
  `test_instruction_surface_parity.py` passes.
- **AC11 — Mutation.** Each change below fails a named test, and the Implementation Result records which:
  - reading the flag when the variable is set (AC1);
  - falling back to `full` on an unknown value (AC1);
  - dropping the station-package rule (AC3);
  - writing no `deferred` entry for a deferred lane (AC4).
- **AC12 — Green, and the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, `pixi
  run -e pyforge-steward pyforge-steward-coverage-gate` (80% on each touched module), `pixi run --frozen -e
  pyforge-core pyforge-core-test`, the platform flag tests in `platform-ci-test` and `pixi run --frozen -e
  pyforge-guild lint-types` exit 0. Each changed governed path gets a surface-reconcile entry on the memlog of every
  Spec that governs it, then one scoped stamp per Spec, and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Key every lane by `(task, environment)`.
- Derive a lane's paths and station from `pixi.toml` and the environment name; never a hand-kept table.
- Keep the journal additive, and keep `run_preflight`'s default `full`.
- Name every deferred lane on stdout and in the journal.
- Reconcile every governed path on each governing Spec's memlog, then stamp each scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never change `scripts/pre_push_preflight.sh`, `pixi.toml`, a workflow, or the meaning of `PYFORGE_PREFLIGHT_SKIP`.
- Never fall back silently: an unknown scope refuses, and an unreadable diff says it ran everything.
- Never let the touched scope run a lane `full` would not run, except the five fast-core detectors in place of
  `detectors-ci`.

**Residual risk:**
- A touched push can be green locally and red in CI on a lane it deferred; CI arbitrates, by the operator's ruling,
  and `verify-deferred` is the catch-up. The PR is the gate, as before.
- A change to a repo-root script that only `tests/scripts` exercises defers the scripts suite unless a test file
  changes with it.
- `preflight_budget` judges a touched run by its CI selection, not by the lanes it ran. A follow-up may teach it the
  scope.
- `pixi.toml`'s `pr-preflight` description still says it runs the same lanes as `pr-preflight-lanes`, which has not
  been true since Story 71.2. It is not edited here, because a `pixi.toml` change fires every station suite in CI and
  needs an `environment.yaml` re-export.

## I/O & Edge-Case Matrix

| Situation | `full` (today) | `touched` |
|---|---|---|
| `PYFORGE_PREFLIGHT_SCOPE` unset, flag on (dev) | — | touched |
| `PYFORGE_PREFLIGHT_SCOPE` unset, flag off | full | — |
| `PYFORGE_PREFLIGHT_SCOPE=full` / `touched` | full | touched |
| `PYFORGE_PREFLIGHT_SCOPE=bogus` or empty | exit 2, no lane | exit 2, no lane |
| `PYFORGE_PREFLIGHT_SKIP=1` (any scope value) | the hook skips, journaled | the hook skips, journaled |
| diff under `src/shared/packages/pyforge-steward/src/` | every selected lane | steward test and gate, lint and types, fast core |
| diff to `pixi.toml` only | every station suite and gate | fast core only |
| diff to `scripts/lint_types.py` | lint lanes and the rest selected | the lint lanes, fast core |
| diff unreadable (no `origin/main`) | every lane | every lane, said on stdout |
| a journal record without `mode` | — | read as `full`, nothing deferred |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-159 (the preflight: lane list, selection, concurrent runner,
  journal, budget). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (CI and estate follow-ups) entry, its
  2026-10-15 addition (CI arbitrates the deferred lanes).
- Epic: Epic 103, whose heading now names this feature. Epics 71, 88, 90 and 98, which shipped CAP-159, are `done`.
- Ledger key: `103-6-a-touched-scope-preflight-leaves-the-other-lanes-to-ci-and-verify-deferred-catches-up`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-steward` memlog records the approval, the evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."103"` gains the flag tree, the overlay, steward's flag inventory,
  the core and platform flag tests and `AGENTS.md`.
- Minted 2026-10-15 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding). It runs `src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py`,
  which runs the key `pyforge.steward.preflight_ci_arbitrates` in both states with
  `pyforge.testing_kit.flags.flag_states` (AC1, AC3-AC5), and
  `src/shared/packages/pyforge-steward/tests/unit/test_preflight_verify_deferred.py` (AC6-AC8).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_verify_deferred.py -q` — expected: exit 0.
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_lint_types_gate.py -q` — expected: exit 0 (AC2, the hook's two tests; amended in implementation).
- The AC11 mutations, one at a time, re-running the named test each time — expected: each fails the named test. Revert each.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate` — expected: exit 0.
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: exit 0 (`src/shared/packages/pyforge-core/tests/unit/test_flags.py`, AC9).
- `src/platform/tests/test_openfeature_file_flags.py` in `platform-ci-test`, from `src/platform` — expected: exit 0 (AC9).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` and `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0, and the inventory lists the key on CAP-159 (AC9).
- `pixi run --frozen -e pyforge-guild governance-currency` and `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` — expected: exit 0 (AC10).
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps (AC12).

## Implementation Result

Hand-implemented on branch `chain-steward-103-6-preflight-ci-arbitrates-2026-10-15`, from baseline `fccf4f3ee7`.
The diff is for an independent review against this spec, not against this summary.

- **The scope** (`preflight.py`): `resolve_scope` reads `PYFORGE_PREFLIGHT_SCOPE`, and the flag only when the
  variable is unset. `main` resolves it and refuses a bad value or a flag-tree error with exit 2.
  `run_preflight(scope=..., scope_source=...)` defaults to `full` and refuses an unknown scope with exit 2.
- **The cut**:
  - `preflight_ci.touch_verdict` applies the three rules (station package, a path the command names, lint and
    types). `touched_paths`, `station_package_dirs`, `command_paths` and `lint_types_tasks` derive their input from
    the selection, the environment name and `pixi.toml`.
  - `preflight.touched_cut` keeps the touched lanes and their dependencies, and puts the fast core in
    `detectors-ci`'s place and environment. Everything else is deferred.
  - On the live lane list, with all 37 lanes selected:
    - a change to `preflight.py` keeps 8 (the steward test and gate, and the six `lint-types` lanes, `mypy` in
      `pyforge-foundry-full` among them) and adds the five detectors;
    - a `pixi.toml`-only change runs the five detectors alone;
    - `docs-site/scripts/validate-doc-links.js` keeps `docs-site-validate-links@site`;
    - `tests/scripts/test_docs_map_render.py` keeps `pyforge-doctor-scripts-test@pyforge-ci` and
      `docs-map-render-test@pyforge-guild`;
    - a CFE test change keeps `test-ci@local-recipes`.
- **The journal:** the run record and the interrupted record gain `mode` and `deferred`. The stdout block names the
  scope, its source, the fast core and every deferred lane. The stderr count line adds the deferred count.
- **The duty:** `preflight_verify.py`'s `PreflightDuty` and `verify_deferred`; `cli.py` registers `preflight` as
  the thirtieth duty, with `verify-deferred --since`.
- **The flag:** `flags.json`, `flag-overlays.json`, `test_flags.py` (`_SHIPPED_CLOCKS`, the per-environment
  table), `test_openfeature_file_flags.py` (`_SHIPPED_BOOLEANS`), and steward's flag inventory, regenerated, where
  CAP-159 lists the key. `test_console_parity_homes.py` registers no flag and was not changed. Only steward's
  inventory was kept; the other seven stations' regenerated reports were restored, since their drift is theirs.
- **Tests:** `test_preflight_scope.py` (AC1, AC3-AC5) and `test_preflight_verify_deferred.py` (AC6-AC8).
  - *Amended in implementation:* AC2's two hook tests live in `tests/scripts/test_lint_types_gate.py`, beside the
    hook's other tests. In steward's suite, a read of `scripts/pre_push_preflight.sh` fails
    `test_station_tests_trigger_map.py`, because that path does not fire steward's CI job. A live-lane-list test
    failed it the same way, since it handed the repository root to the code under test. It was dropped; the
    live-list examples above were measured by hand.
- **AC11:** each mutation failed named tests in `test_preflight_scope.py`:
  - reading the flag while the variable is set failed all four `test_the_variable_wins_and_the_flag_is_not_read`
    cases;
  - falling back to `full` on an unknown value failed the four `test_an_unknown_scope_refuses` cases and
    `test_main_refuses_an_unknown_scope_and_starts_no_lane`;
  - dropping the station-package rule failed `test_a_station_package_change_keeps_that_stations_lanes`,
    `test_the_portal_package_is_the_stations_too` and `test_a_touched_run_runs_the_cut_and_journals_what_it_deferred`;
  - journaling no `deferred` entry failed `test_a_touched_run_runs_the_cut_and_journals_what_it_deferred` and
    `test_an_interrupted_touched_run_journals_its_scope_and_what_it_deferred`.
- **Green**, each read from its own exit code:
  - `pyforge-steward-coverage-gate`: exit 0, 2708 unit tests passed. Touched modules: `cli.py` 99%, `preflight.py`
    94%, `preflight_ci.py` 82%, `preflight_verify.py` 97%.
  - `pyforge-core-test`: exit 0 (2461 passed).
  - `test_openfeature_file_flags.py` in `platform-ci-test`: exit 0 (52 passed).
  - `test_lint_types_gate.py` in `pyforge-ci`: exit 0 (30 passed).
  - `lint-types`, `flag-gate-check`, `governance-currency`, `test_instruction_surface_parity.py` and the planning
    checks: exit 0.
  - `pyforge-steward-test` is recorded on the PR.

## Spec Change Log

- 2026-10-15: minted from the Dream's 2026-10-15 addition (CI arbitrates the deferred lanes), under the operator's
  three rulings of that day. `type: feature`, behind the new flag `pyforge.steward.preflight_ci_arbitrates`; no CAP.
  Bound to `spec-pyforge-steward` CAP-159.
- 2026-10-15 (implementation): AC2's hook tests moved to `tests/scripts/test_lint_types_gate.py`, since the
  station-test trigger map refuses a steward test that reads the hook script (Implementation Result, amended). No AC
  changed.
