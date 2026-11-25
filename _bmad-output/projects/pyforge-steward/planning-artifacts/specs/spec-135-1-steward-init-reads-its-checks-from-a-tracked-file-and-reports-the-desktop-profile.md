---
title: '135.1: Steward init reads its checks from a tracked file and reports the desktop profile'
type: 'feature'
created: '2026-11-25'
status: 'done'
story: 135-1-steward-init-reads-its-checks-from-a-tracked-file-and-reports-the-desktop-profile
spec: spec-pyforge-steward
difficulty: 'hard'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a readiness check is a detector: it reads the machine and reports; a gated check is a silent green (roster list)
surface:
  - 'docs/governance/machine-readiness.yaml'
  - 'docs/governance/machine-readiness.schema.json'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/machine.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/estate_realize.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/session.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_machine.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_bootstrap*.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_cli.py'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_machine_readiness_data.py'
  - 'src/shared/packages/pyforge-steward/README.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/oracle-map.md'
  - 'docs/reference/station-cheat-sheet.md'
  - 'docs/governance/realization-register.yaml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/realization-register.yaml
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** No verb answers "can this machine do this kind of work". Measured on a new macOS laptop (osx-arm64) on 2026-11-25:

- `steward init` reads `_PREREQ_ORDER = ("pixi", "git", "gh", "podman")` from `bootstrap.py`: each is on `PATH` and its `--version` parses, and only pixi has a floor (`requires-pixi` of `pixi.toml`). It exited 1 on podman alone.
- `steward validate-fast` runs the same four, the `environment.yaml` sync and a `steward --version` smoke, and stops at the first failure: it exited 1 on podman alone, so `validate-fast` and `initrepo` cannot be green on a machine with docker, or with no engine, whatever work it does.
- `steward session check` gives seven findings for one session and looks at `pyforge-guild` only. `provision --list` lists 36 environment names with no platform and no materialized state. `estate realize --plan` lists due package names and runs no probe. `mason doctor` and `warden scan --doctor` each report their own station.
- Nothing reports the git identity, the installed hooks, the locale, whether an environment is in the lock for this platform (six environments are linux-64 only) and materialized, or whether the scribe PostgreSQL cluster, the platform servers and Chromium answer. The laptop met each of these as a failing lane.

**Approach:** Extend `init`; add no duty (the duty count stays 31).

*The data.* `docs/governance/machine-readiness.yaml`, held to `docs/governance/machine-readiness.schema.json` (`$id: urn:local-recipes:governance:machine-readiness`), beside the realization register and pointing into it where a probe already exists there:

```yaml
version: 1
profiles:
  <id>: {title, requires: [<id>...], platforms: [linux-64, osx-arm64, win-64]?}
checks:
  - id: <kebab, unique>
    profile: <id>
    class: software|configuration|environment|usable
    severity: required|advisory      # advisory never changes the exit code
    cost: cheap|deep                 # default cheap
    platforms: [...]?                # the row applies only there; elsewhere its status is na
    needs: [<check id>...]?          # a failed need gives status blocked and the probe is not run
    what: <one sentence>
    probe: {<one kind of the closed set>}
    remedy: {command: <exact command>, who: agent|operator, where: any|primary-checkout?, doc: <docs path>?}
    declared_in: <tracked path a floor or a value is read from>?
```

This story writes all five profile entries (`desktop`; `container` requires `desktop`; `pod`, `ocp` and `nkp` require `container`; `nkp` has `platforms: [linux-64]`) and every `desktop` row: `pixi`, `git`, `gh`, `gh-auth`, `git-identity`, `git-hooks`, `locale-utf8` (advisory), `env-guild`, `env-preflight-lanes`, `env-yaml-sync`, `bmad-method`, `station-clis`, `station-clis-own-env`, `token-kit` (advisory), `scribe-pg`, `platform-servers`, `playwright-chromium`, `manticore-studio` (advisory).

*The probes.* A new module `machine.py`, a peer of `bootstrap.py` and `session.py`, with the injected runner seam those two have. Its probe kinds are a closed set, each written once; this story writes the ones the desktop rows use:

| kind | what it reads |
|---|---|
| `tool` | `{name, version_argv?, floor?: {pixi-requires: true} or {literal: "x.y.z"}}`: on `PATH`, the version parses, at or above the floor |
| `command` | `{argv, env?, expect_exit: 0, stdout_match?, timeout_s?}`; with `env`, it runs as `pixi run --as-is -e <env> ...` and only when that environment is materialized |
| `environments` | `{names: [...]}` or `{from: preflight-lanes}`: `pixi.lock` carries the environment for this platform and `.pixi/envs/<name>/conda-meta/pixi` exists; an environment the lock lacks here is `na`, naming the lanes it removes |
| `session-finding` | `{name: gh-auth|bmad-method|token-kit|codegraph-index}`: composed from `session.py` |
| `register-probe` | `{package: <realization-register row>}`: composed from `estate_realize.run_probe` |
| `env-sync` | composed from `provision.check_environment_sync` |
| `git-config` | `{keys: [user.name, user.email]}` |
| `git-hooks` | `{types: [commit-msg, pre-push]}`: the files under the hooks directory of `git rev-parse --git-common-dir` |
| `locale-utf8` | `locale charmap` prints `UTF-8` |

A row's status is one of `ok`, `fail`, `blocked`, `skipped`, `na`. A probe that cannot launch is a failed row, never a crash.

*The verb.* `steward init [--profile NAME ...] [--class {software,configuration,environment,usable} ...] [--deep] [--list] [--repo PATH] [--json]`. A bare `init` is `--profile desktop`; `--profile all` is every profile. A profile is ready when every `required` row of it and of the profiles it requires is `ok`. Exit codes are steward's existing ones: 0 every chosen profile is ready (also `--list`); 1 a chosen profile is not ready, or is unsupported on this platform; 2 an unknown profile or class; 3 the data file is missing or fails its schema (a documented refusal: the verb cannot judge); 70 a crash. The text report is one block per profile, a line per row (`ok`, `FAIL`, `WARN`, `BLOCKED`, `skip`), each `FAIL` followed by `remedy (agent|operator): <command>`, then `steward init: <profile> READY` or `NOT READY`. `--json` carries `ok`, `platform`, `root`, `data`, `profiles[]` (`id`, `ready`, `supported`, `requires`, `counts`), `checks[]` (`id`, `profile`, `class`, `severity`, `status`, `what`, `found`, `required`, `detail`, `composes`, `remedy`) and the earlier `prereqs` array in its old shape.

*Composition.* `gather_prereqs` returns the desktop software rows (`pixi`, `git`, `gh`), so `validate-fast` and `initrepo` no longer need a container engine. `session check`, `provision --verify`, the register's probes and `scribe-pg-status` are called, never written again. `mason doctor` and `warden scan --doctor` are run as smokes of their stations and read by exit code, never by import (CAP-182).

*Confirm or drop, before composing.* (a) Prove that `estate_realize.run_probe` and its runner neither install nor write when called from here (its probes run `--as-is`); if they do, give `register-probe` its own `--as-is` runner. (b) The register's `playwright` row still lists `python -m playwright install chromium` as a realize step though Story 131.1 moved the browsers into the lock: correct the row if it is stale, in this surface. (c) The shared hooks directory on this laptop holds `commit-msg` and `pre-push` and no `pre-commit` file: the `git-hooks` row checks the two types `scripts/precommit_config_check.py` requires; record what was found.

*Contract.* `contract.md`: the `steward init` row gains the flags and the capability; the exit-code table gains the refusal row for `init`; "What steward needs from the tree" gains the data file and its schema. `oracle-map.md` gains the CAP-183 row (`machine.py`, `bootstrap.py`, `cli.py`; `test_machine.py` in the package half, `test_machine_readiness_data.py` in the live-tree half). `docs/reference/station-cheat-sheet.md` is regenerated. The surface reconcile is appended to the memlog of `spec-pyforge-steward` and of its co-governor `spec-pyforge-core` before the scoped stamps.

Ledger key: `135-1-steward-init-reads-its-checks-from-a-tracked-file-and-reports-the-desktop-profile`.

### Living CAP citations

- spec-pyforge-steward CAP-183 (minted 2026-11-25), FR-57 ← CAP-183; amends what CAP-48's `init` reports; composes CAP-5, CAP-167 and CAP-175 (no text change); AD-1, AD-8.

## Boundaries & Constraints

**Always:**
- Keep `init` read-only: an in-environment probe runs with `pixi run --as-is` and only in a materialized environment; otherwise the row is `blocked` on its environment row.
- Keep the `prereqs` array of `init --json` in its old shape, so its current readers do not break.
- Print a remedy for every row that is not `ok`, with `who`; an installer and a sign-in are `operator`; a remedy with `where: primary-checkout` says so in the printed line (`steward setup` installs hooks and never runs from a linked worktree).
- Where a composed verdict can fail for a reason that is not the machine's (a BMAD pin that drifted, a chart that does not render), say so in the row's remedy.
- Return a `DutyResult`; a duty never calls `sys.exit` (AD-8).

**Never:**
- Never add a duty, a feature flag, an MCP target or a repo detector; the data file's schema and referential integrity are held by a steward meta-test.
- Never install, sign in, start a server or write a file from `init`; no `--fix`.
- Never print the value of a variable, a token or the content of a file a row checks.
- Never import another station's package from steward's source.
- Never write a requirement into `machine.py` that a data row can carry.

## Acceptance Criteria

**Given** `steward init` checks pixi, git, gh and podman from a list written in `bootstrap.py`, fails every machine without podman, and `validate-fast` and `initrepo` fail with it; and nothing reports whether gh is signed in, the git identity and hooks are set, the locale is UTF-8, each environment a preflight lane uses is in the lock for this platform and materialized, or the station CLIs, the scribe database, the platform servers and Chromium answer
**When** `docs/governance/machine-readiness.yaml`, held to `machine-readiness.schema.json`, lists the profiles and every desktop check, a new module `machine.py` loads it and runs each row's probe from a closed set of kinds, and `init` gains `--profile`, `--class`, `--deep`, `--list` and `--repo`, a bare `init` being the desktop profile
**Then** `steward init` exits 0 when every required desktop row is ok and 1 otherwise, each row that is not ok printing `remedy (agent|operator): <command>`; `--list` prints the profiles and rows and probes nothing; an unknown profile or class exits 2; a missing or schema-invalid data file exits 3; and `--json` carries `ok`, `platform`, `profiles[]`, `checks[]` with `status`, `detail` and `remedy.who`, and the earlier `prereqs` array
**And** `steward init` and `steward validate-fast` exit 0 on a machine with no container engine on `PATH`, since podman is no longer a desktop row
**And** no run of the verb changes `.pixi/`, the working tree or the git hooks, proven by a test; a meta-test fails when a row names an environment `pixi.toml` lacks, a register package or session finding that does not exist, a remedy without `who`, or a floor that differs from the file it is declared in; and `contract.md`, `oracle-map.md` and the station cheat sheet carry the verb as it now is

- **AC1 — The loader, each probe kind, the statuses and both reports are held by unit tests**, with a fake runner: each kind's `ok` and `fail`, `needs` giving `blocked`, `platforms` giving `na`, an advisory row never changing the exit code, `--list` calling no probe, exit 2 on an unknown profile or class, exit 3 on a missing and on a schema-invalid data file, and the `prereqs` array in its old shape. One test fails by name when a run of `init` changes `.pixi/`, the working tree or the hooks directory. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_machine.py -q
  ```

- **AC2 — The data file is held to the tree.** The meta-test (`live_tree`) fails by name when the file breaks its schema, a row names an environment `pixi.toml` lacks, a register package or a session finding that does not exist, a `needs` id or a profile that is not defined, a remedy without `who`, or a floor that differs from the file named in `declared_in`. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_machine_readiness_data.py -q
  ```

- **AC3 — `validate-fast` no longer needs a container engine.** A test in the bootstrap modules fails by name when `gather_prereqs` returns a container engine or `validate_fast_steps` fails with none on `PATH`. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_bootstrap.py src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_remedies.py src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup.py src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup_flow.py -q
  ```

- **AC4 — The listing probes nothing and exits 0.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pyforge steward init --list
  ```

- **AC5 — An unknown profile is a usage error.** Expected: exit 2.

  ```bash
  pixi run --frozen -e pyforge-guild pyforge steward init --profile no-such-profile
  ```

- **AC6 — The duty count did not move, and the public contract and the oracle map hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q
  ```

- **AC7 — Both halves of steward's suite pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test && pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC8 — The generated station page matches the CLI.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-station-cli -- --check
  ```

- **AC9 — The realization register still validates.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild realization-register-check
  ```

- **AC10 — The desktop run on this laptop is recorded.** The Spec Change Log holds one line with the verdict `steward init --json` gave on this machine (`READY` or `NOT READY`), its counts, and each row that was not ok with its remedy's `who`. Expected: prints 1, exit 0.

  ```bash
  grep -c -E "desktop run on this laptop: (READY|NOT READY) - " _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-135-1-steward-init-reads-its-checks-from-a-tracked-file-and-reports-the-desktop-profile.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-183 (minted 2026-11-25), FR-57 ← CAP-183; amends what CAP-48's `init` reports; composes CAP-5, CAP-167 and CAP-175 (no text change); AD-1, AD-8.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the open rows close, and one verb says whether a machine is ready); operator rulings of 2026-11-25: "this machine is missing several software / configutation items - becuase it was a new machine - shouldnt there be a way to check that all required software (docker, ocp etc) and all required configuration (gh, env variables) and all enviornments resolved and work on this new machine", "doccumentations procedures, autmation enviornment setup and checks should be part of onboarding a new developer, a new machine to build. test, verify and run pyforge locally - on a desktop, as a container, as a pod etc", "Plan and build now".
- Epic: Epic 135, minted with this story.
- Ledger key: `135-1-steward-init-reads-its-checks-from-a-tracked-file-and-reports-the-desktop-profile`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."135"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's rulings of the same date. Not implemented. Measured at mint on this laptop (osx-arm64, pixi 0.84.2): `steward init --json` exit 1 on podman alone; `steward validate-fast` exit 1 on podman alone; `provision --verify` exit 0; `docker`, `podman`, `kind`, `kubectl`, `helm`, `oc`, `crc`, `nic`, `uv`, `node` and `codegraph` not on `PATH`; `LANG` and `LC_ALL` unset; the shared hooks directory holds `commit-msg` and `pre-push`.
- 2026-11-25: implemented; status `in-review`. Built: `docs/governance/machine-readiness.yaml` with its schema (five profiles; 21 desktop rows, the 18 this spec names plus `warden-doctor`, `mason-recipe` and `estate-verified`, all three advisory), `machine.py` (loader held to the schema's rules, the closed probe kinds, statuses, text and `--json` reports, `MachineDeps` seam), `init --profile/--class/--deep/--list/--repo` (duty count still 31), `gather_prereqs` from the desktop software rows (pixi, git, gh: podman left `validate-fast` and `initrepo`), `session.machine_findings` (the four findings, run `--as-is`). Deviations: the `locale-utf8` probe reads `LC_ALL`, `LC_CTYPE`, `LANG` rather than `locale charmap`, because CPython coerces its own `LC_CTYPE` to UTF-8 under a C locale and a child's `locale charmap` then prints UTF-8 (measured); a `command` row may carry `{platform}` in `argv`/`stdout_match` and a `miss_note` (no new probe kind). Confirm-or-drop: (a) `estate_realize.run_probe` runs `pixi run --as-is -x`, and `.pixi/envs/<env>/conda-meta/pixi` kept its mtime across an `--as-is` run (an outer `pixi run --frozen` refreshes it; the tutorial says so); (b) the register's `playwright` row was stale and now has no realize step; (c) the shared hooks directory holds `commit-msg` and `pre-push` and no `pre-commit` file; `git-hooks` checks the two types `scripts/precommit_config_check.py` requires. Open: CAP-183 is not yet in SPEC.md, so `test_public_contract`, `test_oracle_map` and `test_cap_citations` fail on it in the live-tree half (each passed in a scratch copy with the prepared render applied); the spec-surface memlog entries and scoped stamps are not done.
- 2026-11-25: desktop run on this laptop: NOT READY - `steward init --json` exit 1 (osx-arm64); desktop counts ok 15, fail 1, blocked 0, skipped 0, advisory 5, na 0; required not ok: `env-preflight-lanes` (agent: `pixi install --frozen -e` pyforge-foundry-full, site, pyforge-core, pyforge-testing-kit); advisory WARN: `locale-utf8` (operator), `warden-doctor` (operator), `mason-recipe` (agent; the WARN stays until pyforge-guild carries conda-forge-metadata, the operator's pixi.toml change), `token-kit` (agent), `estate-verified` (agent: no estate verify has confirmed osx-arm64). An earlier run the same day also had `scribe-pg` BLOCKED (agent: `pixi run -e pyforge-scribe-pg scribe-pg-up`) before another session materialized that environment and started the cluster. `steward validate-fast` exit 0 with no container engine on PATH; `init --list` exit 0; `init --profile no-such-profile` exit 2.
- 2026-11-25: review findings closed (test-first). (1) `validate_data` now holds every schema rule: `uniqueItems` on `needs`, `requires` and `platforms`; the patterns of a remedy's `doc`, an `env-or-file` `var`/`key` and a `sysctl` `key` (full match); minimum 0 for `expect_exit` and `min`; a non-empty `any_of` `name` and `label`. The meta-test `test_the_loader_refuses_everything_the_schema_refuses_rule_by_rule` enumerates every `<schema path>:<keyword>` rule of `machine-readiness.schema.json`, breaks each once in the real file and fails by that rule's path when the loader accepts the result (or when no instance exists to break); a schema-invalid file exits 3 (`test_a_schema_invalid_data_file_exits_3`). (2) `needs: [pixi]` on every row whose probe runs through pixi (`station-clis-own-env`, `warden-doctor`, `scribe-pg`, `platform-servers`, `playwright-chromium`, `kubectl-helm`, `nic`); `test_every_row_that_runs_through_pixi_needs_pixi` fails by row name. (3) A BLOCKED or failed row with `{env}` and no measured environment prints one exact command per environment its own probes name (an environments list, the full-preflight lane environments, a command's `env`, a register row's `env`); the placeholder stays only when no name can be read. (4) With `--class` the verdict reads `READY (<classes> checks only)` and each JSON profile carries `classes`. (5) An unknown profile beside `all` exits 2 naming it. (6) `validate-fast` and `initrepo` take each tool's remedy from its desktop row (`bootstrap.prereq_remedies`); `_REMEDIES` is the fallback for a checkout with no data file; both paths tested. The pixi installer remedy is pixi's documented `curl -fsSL https://pixi.sh/install.sh | sh` in the row, the fallback table and `session.py`. Desktop re-run on this laptop: same verdict and rows as recorded above (`NOT READY`, exit 1, `env-preflight-lanes` only); the gh API budget read 4988. With PATH empty, `init --profile all` exits 1 and every environment row is BLOCKED behind `pixi` with exact `pixi install --frozen -e <name>` lines (no `<environment>` printed).
- 2026-11-25: second review findings closed (test-first). (1) A `tool` probe with `any_of` and a top-level `version_argv` was accepted though the schema's `oneOf` refuses it: `_GROUP_KEYS` names the keys each `oneOf` group allows (`tool` with `name`: name, version_argv, floor, found_note; with `any_of`: any_of, floor, found_note; `environments` with `names` or `from` alone), and a key of the other group is refused (`test_a_probe_must_fit_one_of_its_kinds_key_groups`). (2) A list or mapping where the schema wants a string id (a `needs` item, a `requires` item, a row's `profile`, a probe's `kind`) raised TypeError out of `validate_data`; each is now type-checked before its membership test and is a reported problem, and `init` exits 3 (`test_a_list_or_mapping_where_an_id_belongs_is_a_problem_never_a_crash`, eight cases); `test_the_schema_and_the_loader_refuse_the_same_documents` carries the nine new cases, refused by both. (3) `session.py`'s missing-pixi and missing-gh remedies come from `bootstrap.prereq_remedies(root)` (the desktop rows; `_REMEDIES` only when no data file loads), so `session check`, `init`, `validate-fast` and `initrepo` print one remedy per tool; the gh remedy is now the row's `install-gh: pixi global install gh`. Both paths tested in `tests/unit/test_session.py`. `pyforge-steward-test` exit 0 (2160 passed, 14 skipped; 33 passed); `test_public_contract.py` 31 passed; `governance-currency` exit 0; ruff check and format check exit 0. The live-tree half exits 1 on two cases outside this change: `test_capability_ledger_live` (CAP-183, now in SPEC.md, has no capability-ledger row) and `test_skf_steward_skill::test_conda_forge_expert_not_replaced` (Story 134.2's uncommitted conda-forge-expert edits).
- 2026-11-25: closed. Implemented, independently reviewed against this spec, its findings applied and re-reviewed; the full local `pr-preflight` gates the PR that lands it (branch `open-rows-and-onboarding-2026-11-25`).
