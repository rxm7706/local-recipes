---
title: "15.2: Opengrep runs estate-authored rules, and its offline flags are pinned by test"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-15-1-opengrep-is-an-optional-sast-scanner-that-informs-never-publishes-the-verdict.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/sast.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py
  - src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-25 ships the opengrep mechanism with no estate rules and an unpinned offline posture (line numbers at
`03a7aff5d9`):
- The package's `src/shared/packages/pyforge-warden/src/pyforge/warden/data/sast-rules/` holds one file, `planted-opengrep-match.yaml`, a test marker. A production run
  with opengrep enabled detects nothing the estate cares about (WAR-M-C4, WAR-D-C6).
- No test pins opengrep's telemetry-off invocation: `--disable-version-check` (`src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` about :465) and the
  environment `SEMGREP_SEND_METRICS=off` and `OPENGREP_ENABLE_VERSION_CHECK=0` (about :502-503). The socket guard cannot
  see a subprocess's egress, so the argv and env are the only offline proof (WAR-M-C4, WAR-M-D6's CAP-25 half).
- With `WARDEN_OPTIONAL_SCANNERS=opengrep` and the flag `pyforge.warden.sast_opengrep` off, `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` (about
  :1334-1335) strips opengrep silently. Story 15.1's Flag line says "as today", which at mint meant a `PluginError`;
  `test_cli_filters_opengrep_when_flag_off` does not call the CLI, so the shipped behaviour is unpinned. The flip is
  already recorded in `epics.md` § Currency reconciliation — 2026-10-10; Story 15.1's text is not edited.

WAR-M-D6's CAP-23 half is rejected (Story 11.2 decided that runner errors fail open with no note; Story 13.2 narrows
that for a started run). EGM audit 2026-11-01, cluster WAR-CL-10; findings WAR-M-C4, WAR-D-C6, WAR-M-D6, accepted by
the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- Move `planted-opengrep-match.yaml` to `src/shared/packages/pyforge-warden/tests/fixtures/` and make every test that used `bundled_sast_rules_dir()`
  for it pass `rules_dir` explicitly.
- Ship a few estate-authored rules in `data/sast-rules/`, drawn from the Spec's own constraints: `subprocess` with
  `shell=True`, unsafe `yaml.load`, `eval`/`exec`. Each rule has a fixture file that trips it, and a test runs the rule
  set over the fixtures (the real binary where present; the rule files parse as YAML with an `id`, `pattern(s)`,
  `message` and `severity` everywhere).
- Extend `test_opengrep_engine_argv_capture` to capture `kwargs["env"]` and assert the three telemetry-off settings.
- Make `test_cli_filters_opengrep_when_flag_off` drive `warden scan` and pin today's flag-off behaviour (stripped, no
  error).
- CAP-25 success names the telemetry-off argv and env through a `bmad-spec` re-derive.

Ledger key: `15-2-opengrep-runs-estate-authored-rules-and-its-offline-flags-are-pinned-by-test`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-25 (FR-42) — SAST joins as an optional plugin: opengrep with estate-owned rules. A `fix`,
  so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag (`pyforge.warden.sast_opengrep` keeps gating
  the scanner).

## Acceptance Criteria

- **AC1 — Estate rules ship.** Given the built package, When `bundled_sast_rules_dir()` is listed, Then it holds the
  estate-authored rules (at least `shell=True`, unsafe `yaml.load` and `eval`/`exec`) and no file named
  `planted-opengrep-match.yaml`.
- **AC2 — Each rule trips.** Given each estate rule and its fixture, When opengrep runs (the test skips with a reason
  where the linux-64-only binary is absent), Then the report's `advisory` carries a note naming that rule id, the
  fixture path and line; the status and exit code equal the same run with the scanner disabled.
- **AC3 — The planted marker is a fixture.** Given `src/shared/packages/pyforge-warden/tests/fixtures/`, Then it holds the planted rule, and every
  test that runs it passes `rules_dir`.
- **AC4 — The offline posture is pinned.** Given `test_opengrep_engine_argv_capture`, When it captures the subprocess
  call, Then it asserts `--disable-version-check` in the argv and `SEMGREP_SEND_METRICS=off` and
  `OPENGREP_ENABLE_VERSION_CHECK=0` in `kwargs["env"]`; removing any one of them from `engines.py` turns it red
  (mutation, reverted).
- **AC5 — Flag-off is pinned through the CLI.** Given `WARDEN_OPTIONAL_SCANNERS=opengrep` and the flag off, When
  `warden scan` runs, Then opengrep does not run, no error is recorded, and the exit code equals a default run.
- **AC6 — The contract follows.** CAP-25 success names the telemetry-off argv and env through a `bmad-spec` re-derive,
  never a hand edit.
- **AC7 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` passes.

## Boundaries & Constraints

**Always:** SAST results stay advisory notes, never a `Finding`, a rung, a status or an exit code; rules ship in the
package's data and are never fetched from a registry; an absent binary is omit-not-error (Story 9.3).

**Never:** add a registry `--config`; change the `ComplianceReport` version (1.1.0); edit Story 15.1's text in
`epics.md` (its Flag and Deps lines stay as the 2026-10-10 currency section records them); hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-25 (FR-42) — SAST joins as an optional plugin: opengrep with
  estate-owned rules; a fix, no new CAP.

Parent: CAP-25

- EGM audit findings carried: WAR-M-C4, WAR-D-C6, WAR-M-D6 (its CAP-25 half; cluster WAR-CL-10; accepted 2026-11-01;
  one memlog event each on `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 15 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `15-2-opengrep-runs-estate-authored-rules-and-its-offline-flags-are-pinned-by-test`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/data/sast-rules/`, `src/shared/packages/pyforge-warden/tests/fixtures/`, `src/shared/packages/pyforge-warden/src/pyforge/warden/sast.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py`,
  `src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py -q` — expected: pass, including the env
  assertions and the CLI flag-off test.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: done

Summary: implemented 2026-11-01 in the EGM audit landing worktree (branch `egm-audit-2026-11`), uncommitted for the
session owner to land. AC1-AC5 and AC7 are met and tested. AC6 is handed to the re-derive phase as a memlog event,
because `SPEC.md` is never hand-edited.

### Dev notes: what changed

- **Estate rules (AC1).** `src/shared/packages/pyforge-warden/src/pyforge/warden/data/sast-rules/` now holds three
  rules drawn from the Spec's Constraints, and no planted marker:
  - `subprocess-shell-true.yaml`: `subprocess.$FUNC(..., shell=True|1, ...)`.
  - `yaml-unsafe-load.yaml`: `yaml.unsafe_load`/`unsafe_load_all`/`full_load`/`full_load_all`, and
    `yaml.load`/`load_all` unless the loader is `SafeLoader` or `CSafeLoader`, by keyword or position.
  - `eval-exec.yaml`: `eval(...)` and `exec(...)`.
- **Trip fixtures (AC2).** Each rule has a fixture repo, `src/shared/packages/pyforge-warden/tests/fixtures/sast-trips/<rule id>/`,
  holding a `trips.py` and a no-dependency `pyproject.toml`.
  - In `trips.py`, every line ending `# trips` must raise a note, and every line ending `# safe` must not.
  - The test reads the expected lines from these markers instead of hard-coding them.
- **Planted marker (AC3).** `planted-opengrep-match.yaml` moved, by plain `mv` and unstaged, to
  `src/shared/packages/pyforge-warden/tests/fixtures/sast-rules-planted/`.
  - `test_fixture_repo_trips_rule_with_injected_runner` passes `rules_dir=PLANTED_RULES_DIR` and asserts that the
    runner received it.
  - A new real-binary test runs the planted rule over `projects/opengrep_tripped` with `rules_dir`.
- **`sast.py`: two defects the real-binary run exposed.** Both are fixed in the Surface's `sast.py`; `engines.py` and
  `cli.py` are unchanged.
  - **(a) Relative targets found nothing.** `run_opengrep_engine` both runs inside `cwd` and names `cwd` as the scan
    target. A relative `warden scan <dir>` therefore made opengrep look for `<dir>/<dir>` and report nothing, with no
    error. `run_opengrep_advisory` now passes `cwd=target.absolute()`.
  - **(b) Rule ids carried a host path.** opengrep prefixes every `check_id` with the dotted path of the rules
    directory, for example `home.….sast-rules.eval-exec`. `parse_opengrep_json` takes a keyword-only `rules_dir` and
    strips that prefix, so a note names the bare estate rule id.
- **`src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py`.**
  - **AC4.** `test_opengrep_engine_argv_capture` captures `kwargs["env"]` and asserts `--disable-version-check`,
    `SEMGREP_SEND_METRICS=off` and `OPENGREP_ENABLE_VERSION_CHECK=0`. The parent env is set to the opposite values
    (`on`, `1`), so the env assertions hold only because `engines.py` sets them.
  - **AC5.** `test_cli_filters_opengrep_when_flag_off` now drives `warden scan` twice: once as a default run, and once
    with `WARDEN_OPTIONAL_SCANNERS=opengrep` and the flag OFF through a real flag tree. Spies on
    `cli.select_scanner_plugins` and `sast.run_opengrep_advisory` show:
    - opengrep is stripped before plugin selection;
    - opengrep never runs;
    - the errors, status and exit code equal the default run;
    - there is no `scanner-plugins` error and no advisory.
  - **AC2.** `test_each_estate_rule_trips_its_fixture_through_warden_scan` is parametrised over the three rules and
    skips with a reason when the binary is absent.
    - It runs `warden scan <rule id>` from `sast-trips/` (a relative target, as an operator types it) with opengrep
      disabled, then enabled with the flag ON.
    - The advisory notes name exactly that rule id, that fixture path and every `# trips` line, and no `# safe` line.
    - The exit code, the status and every other report key equal the disabled run.
  - **Rule parse check (everywhere).** Every bundled rule file parses with an `id`, `message`, `severity`,
    `languages: [python]` and a `pattern`/`patterns`/`pattern-either` key, and has a trip fixture.
  - **Other new tests.**
    - An AC1 listing test.
    - An AC3 fixture test.
    - A prefix-strip unit test.
    - A test that a relative target reaches the engine absolute.
- **Mutation check (AC4).** Run on a scratch copy of the package placed first on `PYTHONPATH`, never on the shared
  checkout, because another agent is editing `engines.py` in this worktree. Each mutation was reverted, and `cmp`
  confirmed every restore.
  - Removing `--disable-version-check`, `SEMGREP_SEND_METRICS` or `OPENGREP_ENABLE_VERSION_CHECK` from `engines.py`:
    each one turns `test_opengrep_engine_argv_capture` red.
  - Removing the `cli.py` flag-off strip turns the flag-off test red.
  - Reverting either `sast.py` fix turns 4 tests red.
  - Putting the planted rule back in `data/` turns the AC1 test red.
- **Memlog.** Two events on `spec-pyforge-warden/.memlog.md`:
  - The surface reconcile, naming every changed path.
  - The new CAP-25 success line, for the re-derive (AC6).

### Commands run (exit codes)

- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_sast_opengrep.py -q`:
  exit 0, 33 passed, 0 skipped (opengrep 1.30.2 present).
- `pixi run --frozen -e pyforge-warden pyforge-warden-test`: exit 0. The unit and meta segment passed 2212 tests, and
  the integration segment passed 265. `sast.py` branch coverage is 91%.
- `ruff check src tests` and `ruff format --check src tests`, run from `src/shared/packages/pyforge-warden` with the
  guild env's ruff: exit 0 and exit 0.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.warden`, run from the package directory with the guild env's
  mypy: exit 0, no issues in 43 source files.
- `pixi run --frozen -e pyforge-guild lint-types`: **exit 1**.
  - The failure is not this story's. It is an `I001` in `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py`,
    another station's file that is being edited in this shared worktree.
  - The task stops at that first red `ruff` leg. That leg showed `pyforge-warden ok`.
  - The warden `ruff format` and `mypy` legs were run by hand and are green, as listed above.

### Open for the session owner

- **Re-derive CAP-25 success (AC6).** Run `bmad-spec` from the second 2026-11-01 memlog event.
- **Co-governor reconcile.** `spec-pyforge-core` co-governs `sast.py` and the moved
  `data/sast-rules/planted-opengrep-match.yaml` in `scripts/.spec-surface-baseline.json`.
- **Scoped stamps.** Stamp `spec-pyforge-warden` and `spec-pyforge-core`.
- **Stage the move.** The rename is not staged. `git add` the new paths and the deletion together.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-10, findings WAR-M-C4,
  WAR-D-C6 and WAR-M-D6 (CAP-25 half), accepted by the operator; mode in-PR.

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: the `sast.py` diff, the three estate rules, the trip fixtures, the planted rule (byte-identical to HEAD's `data/` copy) and the test diff against AC1-AC7 and the Boundaries; no other test uses the planted rule through `bundled_sast_rules_dir()`; the argv carries no registry `--config` and no `http`.
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - `test_sast_opengrep.py`: 33 passed, 0 skipped, so AC2 ran on the real opengrep 1.30.2.
  - Mutations: removing `--disable-version-check`, `SEMGREP_SEND_METRICS` or `OPENGREP_ENABLE_VERSION_CHECK` from `engines.py` turns `test_opengrep_engine_argv_capture` red each time (AC4); disabling the `cli.py` flag-off strip turns `test_cli_filters_opengrep_when_flag_off` red (AC5); `cwd=target` instead of `target.absolute()` turns 4 red.
  - Carried forward, not held against the story: the CAP success-line change is recorded on `spec-pyforge-warden/.memlog.md`; `SPEC.md` is unchanged, as required, and the line waits for the session owner's `bmad-spec` re-derive.
  - Open for the session owner: stage the rename (the deletion under `data/sast-rules/` and the new fixture together); `scripts/.spec-surface-baseline.json` still names the old path, so `spec-pyforge-core` (co-governor of `sast.py` and that path) needs its reconcile and scoped stamp.
  - Failures: none.
