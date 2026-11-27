---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/machine.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py
  - docs/governance/machine-readiness.yaml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  - scripts/platform-ci-local.sh
  - src/platform/compose/compose.yml
  - pixi.toml
verified: 2026-11-27
---

# Onboard a machine

Take a new machine, or a new developer's laptop, from bare to a verdict you can trust: one command says whether this machine can build, test and run PyForge on a desktop, in a container, or as a pod, and names the exact fix for everything it lacks.

## What You'll Learn

- How to get a bare machine to the point where `steward init` can run.
- How to ask `steward init` whether a machine is ready for a kind of work.
- How to read its report: which checks failed, which fix is yours and which an agent may run.
- What each of the five profiles needs, and which ones your platform can reach.
- How to re-run to a `READY` verdict, and what to run next.

:::note[Prerequisites]
- A macOS, Linux or Windows machine with a shell and a network connection. Nothing else: Step 0 installs the rest.
- After Step 0, run every command on this page from the repository root.
:::

:::tip[Quick Path]
```bash
pixi run -e pyforge-guild pyforge steward init                      # desktop work
pixi run -e pyforge-guild pyforge steward init --profile container  # plus the image and compose
pixi run -e pyforge-guild pyforge steward init --profile pod        # plus the chart on kind
```
Run each `remedy` line the report prints, then run the command again until it ends in `READY`. The exit code is `0` only when every profile you asked for is ready.
:::

## Understanding the profiles

A profile is a kind of work. Each one includes the profiles it requires, so `--profile pod` also judges `container` and `desktop`.

| Profile | The work | Requires | Needs, in short |
| --- | --- | --- | --- |
| `desktop` | A clone, the environments, the station CLIs, the tests, the full preflight | nothing | pixi, git, gh signed in, git identity and hooks, the preflight's environments, the scribe database |
| `container` | Build and run the platform image and its compose stack | `desktop` | docker or podman with a running daemon, a compose front end, the compose secret |
| `pod` | The platform chart on a kind cluster | `container` | kind, kubectl and helm, a chart that renders |
| `ocp` | OpenShift Local | `container` | crc, oc, the pull secret |
| `nkp` | `steward deploy nic` on kind | `container` | linux-64 only: nic, Docker, the inotify limit |

The checks are rows of `docs/governance/machine-readiness.yaml`, in four classes: `software` (a tool on `PATH`, at the floor the repository declares), `configuration` (a sign-in, an identity, a hook, a variable), `environment` (a pixi environment is in the lock for this platform and installed) and `usable` (a cheap smoke that the thing answers). To see every row without running anything:

```bash
pixi run -e pyforge-guild pyforge steward init --list --profile all
```

`steward init` installs nothing and writes nothing. A probe inside a pixi environment runs with `pixi run --as-is`, which never installs. A check that would start a container or ask a cluster is marked deep and runs only with `--deep`.

## Step 0: Prepare a bare machine

`steward init` runs inside the repository, through pixi, so a bare machine needs four things first: pixi, git and gh, a clone, and a gh sign-in. Each is the operator's step: it installs software, writes to your home directory or signs you in. Run them yourself, in this order. They are the same remedies `steward init` prints for its `pixi`, `git`, `gh` and `gh-auth` checks.

1. **Install pixi** (operator), with the installer from [pixi's installation page](https://pixi.prefix.dev/latest/installation/):

   ```bash
   curl -fsSL https://pixi.sh/install.sh | sh
   ```

   On Windows, in PowerShell: `powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"`. Open a new shell afterwards so `pixi` is on `PATH`.

2. **Get git and gh** (operator). pixi installs both as global tools:

   ```bash
   pixi global install git gh
   ```

   Your OS package manager serves as well (`brew install git gh`, `apt install git gh`; on macOS `xcode-select --install` provides git).

3. **Clone the repository** (operator) and enter it:

   ```bash
   git clone https://github.com/rxm7706/local-recipes.git
   cd local-recipes
   ```

4. **Sign gh in** (operator). It opens a browser or asks for a token; the token is yours, never an agent's:

   ```bash
   gh auth login
   ```

5. **Install the session default environment.** This one an agent may run for you; it installs only what `pixi.lock` already pins:

   ```bash
   pixi install --frozen -e pyforge-guild
   ```

Every command from here on runs from the `local-recipes` directory.

## Step 1: Check the desktop profile

A bare `steward init` is the desktop profile.

```bash
pixi run -e pyforge-guild pyforge steward init
```

This is the report from a new macOS laptop (`osx-arm64`) on 2026-11-25, exit code `1`:

```text
steward init: machine readiness on osx-arm64 (docs/governance/machine-readiness.yaml)
desktop - a clone, the environments, the station CLIs, the tests and the full preflight
  ok      pixi: pixi 0.85.0 (floor >= 0.85.0)
  ok      git: git 2.55.0
  ok      gh: gh 2.102.0
  ok      gh-auth: gh authenticated; 4988 API calls remaining
  ok      git-identity: set: user.name, user.email
  ok      git-hooks: installed in the shared hooks directory: pre-commit, commit-msg, pre-push
  WARN    locale-utf8: the locale does not name UTF-8 (LC_ALL=unset, LC_CTYPE=C.UTF-8, LANG=unset)
          remedy (operator): export LANG=en_US.UTF-8
          note: add the line to the shell profile so every new shell has it
  ok      env-guild: materialized: pyforge-guild
  FAIL    env-preflight-lanes: not materialized: pyforge-foundry-full, site, pyforge-core, pyforge-testing-kit
          remedy (agent): pixi install --frozen -e pyforge-foundry-full
          remedy (agent): pixi install --frozen -e site
          remedy (agent): pixi install --frozen -e pyforge-core
          remedy (agent): pixi install --frozen -e pyforge-testing-kit
          see: docs/how-to/run-and-read-pr-preflight.md
  ok      env-yaml-sync: environment.yaml matches pixi.toml
  ok      bmad-method: no HARD/FAIL integrity findings (via `pixi run -e pyforge-guild bmad-drift-check`)
  ok      station-clis: `pixi run --as-is -e pyforge-guild steward --version` exit 0; `pixi run --as-is -e pyforge-guild marshal --version` exit 0; `pixi run --as-is -e pyforge-guild scribe --version` exit 0; `pixi run --as-is -e pyforge-guild herald --version` exit 0; `pixi run --as-is -e pyforge-guild pyforge doctor --version` exit 0; `pixi run --as-is -e pyforge-guild pyforge mason self-check` exit 0
  ok      station-clis-own-env: `pixi run --as-is -e pyforge-atlas pyforge atlas --version` exit 0; `pixi run --as-is -e pyforge-warden warden --version` exit 0
  WARN    warden-doctor: `pixi run --as-is -e pyforge-warden warden scan --self-check` exited 2: warden's self-check reports a problem; `pixi run -e pyforge-warden warden scan --self-check` prints each one
          remedy (operator): OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY="<a cache directory>" bash scripts/platform-provision-osv-offline-db.sh
          note: that provisions the offline OSV database, the usual problem on a new machine (it downloads; a scan itself stays offline); export the variable in the shell profile afterwards
          see: docs/how-to/scan-for-compliance-with-warden.md
  WARN    mason-recipe: `pixi run --as-is -e pyforge-guild pyforge mason --format json self-check` printed no line matching /"cfe_import_floor_satisfied": true/: mason's self-check finds the CFE import floor incomplete in pyforge-guild, so its recipe verb is unavailable there (`pixi run -e pyforge-guild pyforge mason self-check` names the missing package)
          remedy (agent): pixi install --frozen -e pyforge-mason
          note: pyforge-mason carries the whole floor, so `pixi run -e pyforge-mason pyforge mason recipe ...` works; this row stays WARN until pyforge-guild carries it too, a pixi.toml change that is the operator's
  WARN    token-kit: caveman-skill: instrument-unavailable; codegraph-index: instrument-unavailable
          remedy (agent): pixi run -e pyforge-guild marshal seed kit --apply
          note: the caveman half is the operator's: `caveman-install --only claude --with-hooks`
  ok      scribe-pg: `pixi run --as-is -e pyforge-scribe-pg python scripts/scribe_pg.py status` exit 0
  ok      platform-servers: postgresql reads live in platform-dev; redis-server reads live in platform-dev
  ok      playwright-chromium: playwright reads live in pyforge-atlas
  ok      manticore-studio: bmad-manticore reads live in pyforge-guild
  WARN    estate-verified: `pixi run --as-is -e pyforge-guild pyforge steward estate status` printed no line matching /(?m)^osx\-arm64: .*verdict=confirmed/: no estate verify has confirmed osx-arm64; another platform's run marks it lock-solved at best (`pixi run -e pyforge-guild pyforge steward estate status` prints each platform's verdict)
          remedy (agent): pixi run -e pyforge-steward pyforge steward estate verify
          note: it installs the default tier into a detached worktree, runs its lanes and writes a journal under .steward/estate-refresh/; a red row in that journal names the environment or lane to fix (long-running)
          see: docs/how-to/refresh-the-estate.md
steward init: desktop NOT READY (not ok: env-preflight-lanes)
```

Read it line by line:

| Line starts with | Meaning | Holds the profile back? |
| --- | --- | --- |
| `ok` | The check passed. | No |
| `FAIL` | A required check failed. Its remedy follows. | Yes |
| `BLOCKED` | The check could not run: a check it needs failed, or its environment is not installed. | Yes |
| `WARN` | An advisory check failed. Fix it when you need what it covers. | No |
| `skip` | A deep check; `--deep` runs it. | No |
| `n/a` | The check does not apply to this platform. | No |

Every `FAIL`, `BLOCKED` and `WARN` prints `remedy (agent): <command>` or `remedy (operator): <command>`. An `agent` remedy is safe for a coding agent to run for you. An `operator` remedy installs software, signs in, or changes your shell or your machine: run it yourself.

On this laptop one required check holds the desktop profile back, and its remedy is an agent's: install the four environments the full preflight still needs. Run those four lines, then the same command again; it exits `0` and ends in `steward init: desktop READY` once no required line is `FAIL` or `BLOCKED`. (This page shows the laptop as it was, before those installs.)

Earlier the same day, before the scribe database had been started, the same run also held the profile back on this line:

```text
  BLOCKED scribe-pg: the environment pyforge-scribe-pg is not materialized
          remedy (agent): pixi run -e pyforge-scribe-pg scribe-pg-up
          note: the task installs pyforge-scribe-pg when it is absent and starts the cluster under var/scribe-pg/
```

The five `WARN` lines do not block. Set `LANG` in your shell profile now: a C locale breaks a bare `initdb` and non-ASCII git arguments. Return to the others when you need what they cover: `warden-doctor` before a dependency scan, `mason-recipe` before recipe work (run it from `pyforge-mason` until the Guild environment carries the package), `token-kit` before a measured session, and `estate-verified` before you claim this platform for the whole estate (no `estate verify` has yet confirmed `osx-arm64`).

:::caution[One remedy is tied to a place]
A remedy that ends in `[from the primary checkout, never a linked worktree]` must run there. Git hooks are shared by every worktree, so `steward setup` installs them from the primary checkout only.
:::

## Step 2: Check the container profile

Run this when you will build the platform image, run `scripts/platform-ci-local.sh` with its image stages, or start the compose stack.

```bash
pixi run -e pyforge-guild pyforge steward init --profile container
```

The report repeats the desktop block, then adds the container block. This laptop has no container engine, so this is a real `NOT READY` report, exit code `1`:

```text
container - build and run the platform image and its compose stack
  FAIL    engine: docker is not on PATH; podman is not on PATH
          remedy (operator): brew install podman && podman machine init
          note: macOS shown; Docker Desktop also serves, and on Linux follow https://podman.io/docs/installation
  BLOCKED engine-daemon: needs engine, which is fail
          remedy (operator): podman machine start
          note: with Docker, start Docker Desktop (or the docker service) instead
  skip    engine-runs-amd64: a deep check; --deep runs it
  FAIL    compose: docker is not on PATH; podman-compose is not on PATH
          remedy (operator): brew install podman-compose
          note: macOS shown; Docker Desktop ships `docker compose`
  FAIL    compose-langflow-secret: LANGFLOW_SUPERUSER_PASSWORD is not set in the environment and src/platform/compose/.env has no LANGFLOW_SUPERUSER_PASSWORD
          remedy (operator): printf 'LANGFLOW_SUPERUSER_PASSWORD=%s\n' '<a local value>' >> src/platform/compose/.env
          note: the file is gitignored; choose the value yourself
  ok      env-container-stages: materialized: platform-ci-test, platform-dev, pyforge-warden
steward init: container NOT READY (not ok: env-preflight-lanes, engine, engine-daemon, compose, compose-langflow-secret)
```

Every remedy here is the operator's: an engine, a compose front end and a secret are yours to install and choose. The secret is checked by presence only; its value is never read out. The verdict line also names the desktop checks that are not ok, because a profile is ready only when the profiles it requires are.

Once an engine is installed, the `engine` line names which one it found and what to pass to `scripts/platform-ci-local.sh` (`--engine podman`, or `PLATFORM_CI_LOCAL_ENGINE=podman`). Then add `--deep` once:

```bash
pixi run -e pyforge-guild pyforge steward init --profile container --deep
```

`--deep` runs `engine-runs-amd64`: it starts one throwaway `linux/amd64` container, which pulls one small image and removes the container when it exits. Every Containerfile here builds for `linux/amd64`, so on an arm64 machine this is the check that emulation works.

## Step 3: Check the pod, ocp or nkp profile

Pick the cluster you will use. Each profile requires `container`.

```bash
pixi run -e pyforge-guild pyforge steward init --profile pod   # the chart on kind
pixi run -e pyforge-guild pyforge steward init --profile ocp   # OpenShift Local
pixi run -e pyforge-guild pyforge steward init --profile nkp   # steward deploy nic (linux-64)
```

The pod block on the same laptop, a real `NOT READY` report (kind is not installed):

```text
pod - the platform chart on a kind cluster
  FAIL    kind: kind is not on PATH
          remedy (operator): brew install kind
          note: macOS shown; elsewhere https://kind.sigs.k8s.io/docs/user/quick-start/#installation
  ok      kubectl-helm: kubernetes-helm reads live in platform-dev; `pixi run --as-is -e platform-dev kubectl version --client` exit 0
  ok      chart-renders: `pixi run --as-is -e platform-dev helm template platform src/platform/deploy/charts/platform --set image.tag=readiness --set sidecar.image.tag=readiness --set mcpHost.image.tag=readiness --set-file flags.tree=src/platform/config/flags.json --set-file flags.overlays=src/platform/config/flag-overlays.json --set flags.environment=dev` exit 0
  skip    cluster-reachable: a deep check; --deep runs it
steward init: pod NOT READY (not ok: env-preflight-lanes, engine, engine-daemon, compose, compose-langflow-secret, kind)
```

`kubectl` and `helm` come from the `platform-dev` environment, so only kind is yours to install. With `--deep`, `cluster-reachable` asks the cluster your kubeconfig names; its remedy is `kind create cluster`.

The ocp block, also a real `NOT READY` report:

```text
ocp - OpenShift Local (crc and oc)
  FAIL    crc: crc is not on PATH
          remedy (operator): crc setup
          note: install crc first from https://github.com/crc-org/crc/releases (or Podman Desktop's OpenShift Local extension)
          see: docs/how-to/ocp-cluster-bringup.md
  FAIL    oc: oc is not on PATH
          remedy (operator): eval $(crc oc-env)
          note: run it in each shell that needs oc
  FAIL    crc-pull-secret: ~/.config/openshift/pull-secret.json does not exist
          remedy (operator): mkdir -p ~/.config/openshift && chmod 700 ~/.config/openshift
          note: then save the pull secret from the Red Hat console as ~/.config/openshift/pull-secret.json and record it in .steward/keys-inventory.yaml
          see: docs/how-to/ocp-cluster-bringup.md
  skip    crc-running: a deep check; --deep runs it
steward init: ocp NOT READY (not ok: env-preflight-lanes, engine, engine-daemon, compose, compose-langflow-secret, crc, oc, crc-pull-secret)
```

The nkp profile runs on linux-64 only, because `nic` is in the `pyforge-steward` environment on that platform alone. On any other machine it reports `unsupported`, with no remedy, and its checks read `n/a`:

```text
nkp - `steward deploy nic` on kind
  n/a     nic: not applicable here: the nkp profile needs linux-64, and this machine is osx-arm64
  n/a     nkp-docker: not applicable here: the nkp profile needs linux-64, and this machine is osx-arm64
steward init: nkp NOT READY (unsupported here: the nkp profile needs linux-64, and this machine is osx-arm64)
```

:::note[What the verb never does]
It never creates or starts a cluster, a podman machine or a compose stack, and never runs `deploy nic up`. Starting those is yours; [OCP cluster bring-up](../how-to/ocp-cluster-bringup.md) and [Host Nebari](../how-to/host-nebari.md) carry the steps.
:::

## What You've Accomplished

You have a verdict per kind of work for this machine, and a list of exact commands for everything it lacks, each marked as yours or an agent's. Nothing on the machine changed while you checked.

```
local-recipes/
├── docs/governance/machine-readiness.yaml   # the profiles and checks you just read
├── .pixi/envs/                              # the environments the remedies install
├── var/scribe-pg/                           # the scribe database, once scribe-pg-up has run
└── src/platform/compose/.env                # your local compose secret (gitignored)
```

From a `desktop READY` verdict, continue with [Getting started](getting-started.md) to build a recipe, [How to run and read the pre-push preflight](../how-to/run-and-read-pr-preflight.md) before your first push, or [Local Platform Development](local-platform-development.md) to run the platform host.

## Quick Reference

| Command | What it does |
| --- | --- |
| `steward init` | Judges the desktop profile. |
| `steward init --profile NAME` | Judges a profile and the profiles it requires. Repeat the flag, or use `all`. |
| `steward init --class CLASS` | Runs only checks of one class (`software`, `configuration`, `environment`, `usable`) and what they need. The verdict line then says so, for example `desktop READY (software checks only)`: it is not the profile's verdict. |
| `steward init --deep` | Also runs the deep checks: one throwaway container, a cluster query. |
| `steward init --list` | Prints the profiles and checks. Probes nothing. |
| `steward init --json` | Prints the report as one JSON document. |
| `steward validate-fast` | The fast gate: the desktop software checks, `environment.yaml` sync, a CLI smoke. |
| `steward session check` | One verdict for the session in hand, including the Tier-3 feed. |

Each is run as `pixi run -e pyforge-guild pyforge <command>`.

| Exit | Meaning |
| --- | --- |
| `0` | Every profile you asked for is ready. Also `--list`. |
| `1` | A profile is not ready, or is unsupported on this platform. |
| `2` | An unknown profile or class, also beside `all`. |
| `3` | The data file is missing or breaks its schema, so the verb cannot judge. |

The `--json` document carries `ok`, `platform`, `root`, `data`, `profiles[]` (`id`, `chosen`, `ready`, `supported`, `requires`, `reason`, `counts`, `classes`: the classes the verdict covers, all four unless `--class` narrowed the run), `checks[]` (`id`, `profile`, `class`, `severity`, `cost`, `status`, `what`, `found`, `required`, `detail`, `composes`, `declared_in`, `remedy`) and `prereqs[]`. The container entry of `profiles[]` from the run above:

```json
{
  "id": "container",
  "chosen": true,
  "ready": false,
  "supported": true,
  "requires": [
    "desktop"
  ],
  "reason": "not ok: env-preflight-lanes, engine, engine-daemon, compose, compose-langflow-secret",
  "counts": {
    "ok": 1,
    "fail": 3,
    "blocked": 1,
    "skipped": 1,
    "advisory": 0,
    "na": 0
  },
  "classes": [
    "software",
    "configuration",
    "environment",
    "usable"
  ]
}
```

## Common Questions

### Why does the pixi version differ from `pixi --version` in my shell?

The report shows the pixi that runs inside `pixi run -e pyforge-guild`, which is the one the environment carries and the one your tasks use. The floor is `requires-pixi` in `pixi.toml`.

### Does running the check change anything?

`steward init` does not: its probes run `pixi run --as-is`, which neither installs nor rewrites an environment. The `pixi run -e pyforge-guild` you launch it with is ordinary pixi: on first use it installs `pyforge-guild`, and each run refreshes that environment's install record.

### Do I need Docker or podman for desktop work?

No. A container engine is a `container` check. `steward init`, `steward validate-fast` and `steward initrepo` pass on a machine with no engine.

### Which remedies can I hand to an agent?

The ones printed as `remedy (agent)`: installing a locked pixi environment, starting the scribe database, applying the token kit. Installers, sign-ins, secrets and shell changes are `remedy (operator)`.

### A check failed, but my machine is fine. Why?

Three checks read the checkout, not the machine: `env-yaml-sync`, `bmad-method` and `chart-renders`. Their remedy notes say so. Fix the checkout, or ask whoever changed it.

### How do I add a requirement?

Add a row to `docs/governance/machine-readiness.yaml`. Only a new kind of probe needs code, in steward's `machine.py`. A steward test holds the file to its schema and to the tree.

## Getting Help

- [How to bootstrap a machine with steward](../how-to/bootstrap-a-machine-with-steward.md) for `setup`, `initrepo`, `shell-init` and `session check`.
- [How to run and read the pre-push preflight](../how-to/run-and-read-pr-preflight.md) when a lane is red on a new machine.
- [Pixi environments](../reference/environments.md) for what each environment carries and where it runs.
- [The documentation map](../MAP.md) for every other page.

:::tip[Key Takeaways]
- One command, `steward init --profile <name>`, answers "can this machine do this kind of work".
- Run the `remedy` lines, yours and the agent's, then run the command again.
- The checks are data. The verb reads; it never installs.
:::
