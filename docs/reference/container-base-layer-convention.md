# Container base-layer convention

This repo ships three Containerfiles, written independently over three
stories and converging on the same shape by accident of authorship:

- `Containerfile` (root) — Story 7.1, the multi-station `pyforge-guild`
  image.
- `src/platform/Containerfile` — Story 10.3, the Django-host
  `python-agent-platform` image.
- `src/platform/compose/dbgpt/Containerfile` — Story 10.5, the isolated
  DB-GPT sidecar image (AD-14 Pattern B deviation).

That convergence is policy, not coincidence, and is written down here so a
future Containerfile — or a future edit to one of these three — has
something explicit to match rather than re-deriving the pattern from
scratch. Two mechanisms enforce it (see "Enforcement" below); this doc is
the third leg, naming the discipline in prose.

## The three pillars

### 1. Every base image is registry-pinned, on every stage, in every Containerfile

Every `FROM` — in every build stage, in all three files — carries an
explicit, non-floating tag. Never bare/untagged (Docker silently defaults
an untagged `FROM` to `:latest`), and never `:latest` literally. All six
`FROM` lines across the three files pin a real, explicit version today:

- `ghcr.io/prefix-dev/pixi:0.77.0 AS builder` (all three files' builder
  stage).
- `ubuntu:24.04` (root `Containerfile`'s runtime stage).
- `registry.access.redhat.com/ubi9/ubi-minimal:9.6 AS runtime`
  (`src/platform/Containerfile` and
  `src/platform/compose/dbgpt/Containerfile`'s runtime stage).

An unpinned or `:latest` base makes the image non-reproducible — the exact
same `docker build` command can produce a different image tomorrow with no
change to this repo's own tracked source.

### 2. The multi-stage pixi-materialization shape

All three Containerfiles follow the same two-stage shape:

1. **Builder stage** — `FROM ghcr.io/prefix-dev/pixi:<tag> AS builder`,
   then `pixi install --frozen -e <env>` to materialize the target pixi
   environment exactly as `pixi.lock` pins it, then
   `pixi shell-hook -e <env> -s bash` to render that environment's
   activation script to a file.
2. **Runtime stage** — a minimal, non-pixi base image that `COPY
   --from=builder` only the materialized environment directory and the
   generated shell-hook script (plus, where applicable, the human-authored
   app code the runtime actually serves) — never the `pixi` binary itself.
   A generated `/entrypoint.sh` sources the shell-hook so every console
   script lands on `PATH` at container start.

This keeps the shipped image lean (no pixi CLI, no package cache, no build
tooling) while still being a deterministic function of the committed
`pixi.lock`.

### 3. Credentials cross the build boundary only via `--mount=type=secret`

Build-time secrets — an Artifactory token, a mirror credential, anything
shaped like one — enter a build **only** through BuildKit's
`--mount=type=secret`, read inline (e.g. `$(cat /run/secrets/...)`) for the
single `RUN` step that needs it. Never `ENV`, never `COPY`, never
persisted into any image layer. None of the three Containerfiles bakes a
credential-shaped value into an `ENV` directive today — the two non-secret
`ENV` variable names that do exist (across three total `ENV` directives:
`HOME` in both `src/platform/Containerfile` and
`src/platform/compose/dbgpt/Containerfile`, and `DJANGO_SETTINGS_MODULE`
in `src/platform/Containerfile` only) are deliberately not secret-shaped,
and the guard test below is written to leave them alone while still
catching a real credential leak.

`scripts/container-gates secrets-scan` is a complementary, but different,
layer: it proves nothing secret-shaped ships in a *built* layer (a
build-time `RUN` step). This pillar — and the guard test enforcing it — is
a *static text* check over the Containerfiles as committed, catching an
`ENV`-declared credential (or an unpinned base) at review time, before any
`docker build` ever runs. See "Enforcement" below for why these stay two
separate checks rather than one merged mechanism.

## Enforcement

Two narrow, single-purpose mechanisms together enforce this convention —
matching this repo's existing pattern of small, non-overlapping checks
rather than one do-everything one:

- **`scripts/pixi_version_registry.py`** — already keeps every
  Containerfile's `ghcr.io/prefix-dev/pixi:<version> AS builder` tag in
  sync with `pixi.toml`'s `requires-pixi` floor (`pixi run -e local-recipes
  pixi-version-check`). Narrow scope: the pixi builder-stage tag only.
- **`tests/packaging/test_containerfile_base_layer_convention.py`** — the
  full sweep this doc otherwise couldn't prove on its own: every `FROM` in
  every stage of all three Containerfiles (builder *and* runtime bases,
  pillar 1) carries an explicit, non-`latest` tag, and no `ENV` key in any
  of the three files matches a credential-shaped deny-list (pillar 3). Pure
  stdlib (`re` + `pathlib` + `pytest`), so it runs in the lean `pyforge-ci`
  env — auto-discovered by `python -m pytest tests/packaging -q`
  (`pyforge-deps-test` pixi task), no wiring change required.

Neither mechanism checks pillar 2 (the multi-stage shape itself) — that
shape is a structural convention, verified by reading the three
Containerfiles against this doc, not by a static grep.

## Scope note

No new base image is built or published by this convention — the upstream
`ghcr.io/prefix-dev/pixi` image stays the base for every builder stage
across all three Containerfiles. Building a repo-owned, pixi-preinstalled
base image is a separate, larger undertaking
(`docs/dreams/pixi-container-image.md`) that stays out of scope until at
least two Containerfiles diverge for reasons a shared custom base would
actually solve — not true today, since all three still follow this one
documented pattern.
