---
title: '135.2: The container, pod, ocp and nkp profiles say what each needs'
type: 'feature'
created: '2026-11-25'
status: 'done'
story: 135-2-the-container-pod-ocp-and-nkp-profiles-say-what-each-needs
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a readiness check is a detector: it reads the machine and reports; a gated check is a silent green (roster list)
surface:
  - 'docs/governance/machine-readiness.yaml'
  - 'docs/governance/machine-readiness.schema.json'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/machine.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_machine.py'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_machine_readiness_data.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-135-1-steward-init-reads-its-checks-from-a-tracked-file-and-reports-the-desktop-profile.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 135.1 ships the data file, the loader and the desktop profile. Nothing yet says what a machine needs to build and run the platform image, run the compose stack, put the chart on kind, run OpenShift Local, or run `steward deploy nic`:

- `scripts/platform-ci-local.sh` needs `$ENGINE` (docker by default, `--engine podman`) for its `images`, `container` and `promotion` stages and exits 2 without it; every Containerfile pins `--platform=linux/amd64`, which on arm64 needs emulation.
- `src/platform/compose/compose.yml` needs `docker compose` or `podman-compose` and refuses without `LANGFLOW_SUPERUSER_PASSWORD`.
- `kind` is in no pixi environment (`.github/workflows/platform-ci.yml` pins v0.32.0); `kubectl` and `helm` come from `platform-dev` and `pyforge-steward`; `nic` is in `pyforge-steward` on linux-64 only.
- `docs/how-to/ocp-cluster-bringup.md` names crc 2.63.0, `oc` and a pull secret at `~/.config/openshift/pull-secret.json`; `docs/how-to/host-nebari.md` names Docker and `fs.inotify.max_user_instances=1024`.

**Approach:** Add the rows of four profiles to `docs/governance/machine-readiness.yaml` and the probe kinds only they use to `machine.py`.

Rows:

| profile | row | what it checks | remedy is |
|---|---|---|---|
| container | `engine` | docker or podman on `PATH`; the report names which, and the `--engine` value for `platform-ci-local` | operator |
| container | `engine-daemon` | `<engine> info` exits 0; needs `engine` | operator |
| container | `engine-runs-amd64` | deep: `<engine> run --rm --platform linux/amd64 busybox true` exits 0 | operator |
| container | `compose` | `docker compose version` or `podman-compose --version` | operator |
| container | `compose-langflow-secret` | `LANGFLOW_SUPERUSER_PASSWORD` is in the environment or a key of `src/platform/compose/.env`; presence only | operator |
| container | `env-container-stages` | `platform-ci-test`, `platform-dev` and `pyforge-warden` are in the lock for this platform and materialized | agent |
| pod | `kind` | `kind version` at or above 0.32.0, `declared_in: .github/workflows/platform-ci.yml` | operator |
| pod | `kubectl-helm` | the register's `kubernetes-helm` probe and `kubectl version --client` in `platform-dev` | agent |
| pod | `chart-renders` | `helm template platform src/platform/deploy/charts/platform` in `platform-dev` exits 0; needs `kubectl-helm`; the remedy says a render error is the chart's, not the machine's | agent |
| pod | `cluster-reachable` | deep: `kubectl cluster-info` exits 0 | operator |
| ocp | `crc` | `crc version` at or above 2.63.0, `declared_in: docs/how-to/ocp-cluster-bringup.md` | operator |
| ocp | `oc` | `oc version --client` exits 0 | operator |
| ocp | `crc-pull-secret` | `~/.config/openshift/pull-secret.json` exists; presence only | operator |
| ocp | `crc-running` | deep: `crc status` reads Running and `oc whoami` exits 0 | operator |
| nkp | `nic` | `pyforge-steward` is materialized and `pyforge steward deploy nic validate` on `src/platform/deploy/nic/my-nebari-local.yaml` exits 0 (its exit 2 with the kill switch `pyforge.steward.nkp_deploy` off is reported as that) | agent; the kill switch is the operator's |
| nkp | `nkp-docker` | docker on `PATH`, and `fs.inotify.max_user_instances` at or above 1024 | operator |

Probe kinds added: `tool` with `any_of` (the first found wins and is named in `found`), `env-or-file` `{var, file, key?}` (presence only), `file` `{path}` (`~` expanded; presence only), `sysctl` `{key, min}` (linux only; `na` elsewhere). A profile whose `platforms` excludes this machine reports `unsupported`: not ready, the reason stated, no remedy. A row with `cost: deep` reports `skipped` without `--deep` and never blocks; with `--deep` it runs, and the help text says the amd64 row pulls one small image.

The meta-test holds three literals to their sources: the kind floor to the pin in `.github/workflows/platform-ci.yml`, the crc floor to the version in `docs/how-to/ocp-cluster-bringup.md`, and the `env-container-stages` names to what `scripts/platform-ci-local.sh` asks for those stages.

`contract.md` changes only if a flag or an exit row moves; this story is expected to add none.

Ledger key: `135-2-the-container-pod-ocp-and-nkp-profiles-say-what-each-needs`.

### Living CAP citations

- spec-pyforge-steward CAP-183 (minted 2026-11-25), FR-57 ← CAP-183; composes CAP-175 and CAP-176 (no text change); pap:AD-16 (which tools pixi provisions and which stay on the system); AD-1, AD-8.

## Boundaries & Constraints

**Always:**
- Keep `init` read-only: only a `--deep` run starts a container, and that container is removed when it exits.
- Report a variable, a file key or a file by presence; state in the row's `what` that the value is never read out.
- Give every row a remedy with `who`; installing an engine, kind, crc or a pull secret is the operator's.
- Report `na` for a row that does not apply to this platform and `unsupported` for a profile that does not; never guess a probe for win-64.

**Never:**
- Never start, stop or create a cluster, a podman machine, a daemon or a compose stack.
- Never run `deploy nic up`, with or without `--yes`.
- Never add a pixi dependency to make a row pass.
- Never print the pull secret, the compose password or any other value a row checks.

## Acceptance Criteria

**Given** Story 135.1's data file, loader and desktop profile, and nothing that checks a container engine and its daemon, a compose front end, the compose secret, kind, kubectl and helm, the chart's render, crc, oc and the pull secret, or what `steward deploy nic` needs
**When** the data file gains the rows of the `container`, `pod`, `ocp` and `nkp` profiles and `machine.py` gains the probe kinds only they use (a tool that is any one of several, a variable or a file key by presence, a file by presence, a sysctl floor), with `needs` giving `blocked`, a profile's `platforms` giving `unsupported`, and rows marked deep running only with `--deep`
**Then** `steward init --profile container` exits 1 with an operator remedy when neither docker nor podman is on `PATH` and names the engine it found and the `--engine` value for `platform-ci-local` when one is; a profile is ready only when every required row of it and of the profiles it requires is ok; `--profile nkp` exits 1 and reports `unsupported` off linux-64; and a deep row reports `skipped` without `--deep` and never blocks
**And** a row that reads a variable or a file reports its presence and never its value
**And** the meta-test fails when the kind floor differs from the pin in `.github/workflows/platform-ci.yml`, the crc floor from `docs/how-to/ocp-cluster-bringup.md`, or the container-stage environments from `scripts/platform-ci-local.sh`; and the story spec records one attended `init --profile container` run on this laptop with its real verdict

- **AC1 — The four profiles are held by unit tests**, with a fake runner, on linux-64 and on osx-arm64: `engine` ok with docker, ok with podman, fail with neither; `engine-daemon` blocked when `engine` fails; a deep row `skipped` without `--deep` and run with it; `nkp` `unsupported` off linux-64; a profile not ready when a required row of a profile it requires fails; `sysctl` `na` off linux. One test fails by name when the output of a row that reads a variable or a file contains the value. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_machine.py -q
  ```

- **AC2 — The three literals are held to their sources.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_machine_readiness_data.py -q
  ```

- **AC3 — The listing names all five profiles.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pyforge steward init --list --profile all
  ```

- **AC4 — Both halves of steward's suite pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test && pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC5 — The public contract holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_public_contract.py -q
  ```

- **AC6 — The container run on this laptop is recorded.** The Spec Change Log holds one line with the verdict `steward init --profile container --json` gave on this machine and each row that was not ok with its remedy's `who`. This laptop has no engine at mint, so the expected record is `NOT READY` with operator remedies. Expected: prints 1, exit 0.

  ```bash
  grep -c -E "container run on this laptop: (READY|NOT READY) - " _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-135-2-the-container-pod-ocp-and-nkp-profiles-say-what-each-needs.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-183 (minted 2026-11-25), FR-57 ← CAP-183; composes CAP-175 and CAP-176 (no text change); pap:AD-16; AD-1, AD-8.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the open rows close, and one verb says whether a machine is ready); operator rulings of 2026-11-25, quoted on Story 135.1's spec, answered "Plan and build now".
- Epic: Epic 135.
- Ledger key: `135-2-the-container-pod-ocp-and-nkp-profiles-say-what-each-needs`.
- Deps: Story 135.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."135"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's rulings of the same date. Not implemented. Not verified at mint, because nothing is installed on this laptop: whether Docker Desktop or a podman machine runs the linux/amd64 images acceptably on arm64, whether `podman-compose` works with `compose.yml`, and whether `locale charmap` is the right measure under pixi's shell. No probe was designed for win-64: its rows report `na`.
- 2026-11-25: implemented; status `in-review`. The container, pod, ocp and nkp rows and the probe kinds `tool` with `any_of`, `env-or-file`, `file` and `sysctl` are in the data file and `machine.py`; `needs` gives `blocked`, a profile's `platforms` gives `unsupported`, `cost: deep` gives `skipped` without `--deep`. The meta-test holds the kind floor to `.github/workflows/platform-ci.yml`, the crc floor to `docs/how-to/ocp-cluster-bringup.md`, the container-stage environments to `scripts/platform-ci-local.sh`, the inotify floor to `docs/how-to/host-nebari.md` and the compose variable to `compose.yml`. No flag or exit row moved beyond Story 135.1's. Not verified: a `--deep` run (no engine, no cluster on this laptop), and whether podman-compose serves `compose.yml`.
- 2026-11-25: container run on this laptop: NOT READY - `steward init --profile container --json` exit 1 (osx-arm64); container counts ok 1, fail 3, blocked 1, skipped 1; not ok: `engine` (operator: `brew install podman && podman machine init`), `engine-daemon` BLOCKED on `engine` (operator), `compose` (operator), `compose-langflow-secret` (operator; presence only, never the value); `engine-runs-amd64` skipped (deep); the profile is also held by desktop's `env-preflight-lanes` (agent). Same day: `--profile pod` exit 1 (`kind` FAIL, operator; `kubectl-helm` and `chart-renders` ok; `cluster-reachable` skipped); `--profile ocp` exit 1 (`crc`, `oc`, `crc-pull-secret` FAIL, operator; `crc-running` skipped); `--profile nkp` exit 1, unsupported off linux-64, both rows `na`.
- 2026-11-25: review findings closed: `kubectl-helm` and `nic` now carry `needs: [pixi]` (so `chart-renders` and `cluster-reachable` reach pixi through `kubectl-helm`), and a BLOCKED `env-container-stages` or `kubectl-helm` prints its own environments as exact commands. Container, pod, ocp and nkp re-run on this laptop: unchanged from the line above (exit 1 each; nkp unsupported off linux-64); the container `--json` profile entry now also carries `classes` (all four).
- 2026-11-25: closed. Implemented, independently reviewed against this spec, its findings applied and re-reviewed; the full local `pr-preflight` gates the PR that lands it (branch `open-rows-and-onboarding-2026-11-25`).
