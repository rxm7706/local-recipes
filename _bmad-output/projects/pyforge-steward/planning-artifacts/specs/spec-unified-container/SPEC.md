---
spec: unified-container
# SHIPPED 2026-08-09: steward Epic 7 "The one-container Guild" closed 5/5, and the
# CAP -> story mapping is one-to-one — CAP-1 -> 7-1, CAP-2 -> 7-2, CAP-3 -> 7-3,
# CAP-4 -> 7-4, CAP-5 -> 7-5 (landed in PR #372). Every capability this contract
# names is delivered and on main.
#
# The four open_questions below stay OPEN on purpose and do NOT contradict
# `shipped`. They are forward scope beyond the five capabilities, not unfulfilled
# contract: Q2 says "decide at epic time" and Q4 says Mode I's design "is out of
# scope". Mode L is what shipped. Mode I, the two-tier split, and the
# baked-vs-bind-mount default are a later revision or a new Spec, not a debt
# against this one.
status: shipped
owner-dream: docs/dreams/unified-container.md
surface:
  - Containerfile                     # multi-stage: pixi-install lean env -> checkout at /pyforge -> entrypoint marshal
  - .dockerignore                     # build-context exclusions (credentials/state-leak + arm64/size gaps closed in 7.1's review pass)
  - pixi.toml                         # new composed `pyforge-container` env (pyforge-ci precedent)
  - scripts/container-gates           # image gates: keys audit --secrets over rootfs; provision --verify + per-station --help smoke
companions:
  # Settles what may ENTER the image (AD-1: the ASGI stack is a
  # `pyforge-steward[dashboard]` extra, never a base dep) and fixes the Mode L / Mode I
  # boundary. Answers Q2 by ratifying the baked checkout, and bounds Q3/Q4 without
  # designing Mode I. Q1's second tier is deferred there with a named trigger.
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/unified-container.md
  - ../../research/technical-steward-pixi-workspace-member-research-2026-07-25.md   # Addendum A3/A4 — the feasibility study this Spec formalizes
  - ../../../pyforge-marshal/planning-artifacts/research/technical-pyforge-unification-2026-08-08.md   # § 2 — the orchestration half
updated: "2026-09-09"
open_questions:
  # RETIRED 2026-09-09 — both were STALE, decided by the architecture run, and the frontmatter
  # comment above already said so, so this file was contradicting itself:
  #  - "One image or two" (batch row stB-B3): `uc:AD-2` (`ARCHITECTURE-SPINE.md:1318-1334`) rules
  #    ONE image, with the second tier deferred-not-rejected under a named trigger — "when recipe
  #    builds need to run inside the container".
  #  - "Baked checkout vs bind-mount" (batch row stB-B4): the spine's own topology ratifies the
  #    baked checkout at `/pyforge` (`ARCHITECTURE-SPINE.md:1291`); bind-mount over `/pyforge`
  #    stays the dev override. "Epic time" was Epic 7, closed 5/5 in PR #372.
  # The two below stay GENUINELY OPEN (batch row stB-B5) — but see the blocker note under each.
  - "Worktree placement for in-container bmad-loop runners (container fs vs
    volume) — deferred with Mode I; Mode L runs loops against a mounted host
    checkout exactly as today."
  - "Whether Mode L and the with-infrastructure Mode I are the same image with
    different mounts/limits, or Mode I forks — nothing here may foreclose
    Mode I, but its design is out of scope."
  - "BLOCKER on both Mode questions (2026-09-09): neither is decidable until the image is built by
    something. No CI workflow and no pixi task builds the root `Containerfile` — the workflow grep
    matches only `src/platform/Containerfile` and the two sidecar files, and `pixi.toml` carries no
    docker/podman build — and `pyforge-steward-container-gates-test` /
    `-container-volumes-test` (`pixi.toml:556`, `:569`) run in ZERO CI jobs. CAP-5 is titled 'the
    image proves itself at build time' and there is no build time. Vessel: new steward Story 48.10."
---

# SPEC — one container, eight stations

## Why

Ship the factory itself — all eight stations, wired the way `marshal init`/genesis
wire a bare-metal install — as a single Podman/Docker image with `marshal` as the
one in-container front door ([[one-front-door]]). The 2026-08-08 feasibility study
(research Addendum A3) concluded this is **an epic-sized effort (~4–6 stories),
not a rearchitecture**: the expensive prerequisites (2026-08-02 station
consolidation, the lean-env `pyforge-ci` precedent, the realized air-gap env-var
doctrine, mount-point-agnostic checkout anchoring) already happened. Owner:
Steward (deployment is the estate); Marshal owns the entrypoint contract.

## Capabilities

- **CAP-1 — one build, whole Guild.** Intent: one `podman build` from a
  multi-stage `Containerfile` produces an image containing the repo checkout,
  a pre-materialized lean composed pixi env (`pixi install` in a build stage —
  `steward provision --env`'s code path reused as the build step), and the eight
  `pyforge-*` station packages; entrypoint `marshal`. Success: `podman run`
  reaches every station's CLI surface; rootless, no daemon, no compose file
  (NFR-1/NFR-2's no-standing-service posture at the container layer).
- **CAP-2 — the image ships the repo at a fixed short path.** Intent: all four
  duty modules (`keys.py`, `provision.py`, `deploy.py`, `budget.py`) locate the
  repo by marker-file walk-ups, and `keys.py` imports CFE's `_http.py` from the
  checkout at import time — so the image ships the checkout at `/pyforge`, not
  wheels into a bare filesystem. Success: every marker walk-up resolves
  in-container unchanged; `/pyforge` also trivially satisfies the >~173-byte
  worktree path-length limit that panics pixi-build-python.
- **CAP-3 — credentials never enter image layers.** Intent: `age` identity files
  arrive as Podman secrets (tmpfs-mounted at run time); `_http.py` routing stays
  env-var-only (`podman run -e`/`--env-file`), so the air-gapped container is the
  same container with different env vars. Success: `steward keys audit --secrets`
  runs over the unpacked image rootfs as a build gate (the shipped scanner needs
  zero changes) and finds nothing; no identity, token, or enterprise URL in any
  layer.
- **CAP-4 — state outlives the container.** Intent: mutable state mounts as
  volumes — `.steward/` (keys inventory, budget ceilings), the gitignored
  `.claude/data/conda-forge-expert/` runtime state, loop homes — so rotation and
  ceiling history survive container replacement. Success: replace the container,
  `steward keys list` / `budget check` answer from the surviving volume.
- **CAP-5 — the image proves itself at build time.** Intent: image smoke gates
  run `steward provision --verify` plus each station CLI's `--help` before an
  image is accepted. Success: a broken station wiring fails the build, not the
  first operator.

## Constraints

- **Strict distroless is off the table.** AD-1 subprocess-wraps `age`,
  `age-keygen`, `pixi`, `git` (plus the `gh` convention); a no-shell,
  no-binaries image contradicts the wrap-never-reimplement doctrine. Target:
  minimal base + pinned lean pixi env, multi-stage.
- **Do not bake `local-recipes`** (1,102 packages / ~9.8 GB — the env that blew
  the 10 GB Actions cache and forced `pyforge-ci`). Compose a lean
  `pyforge-container` env from the `pyforge-*` family the same way; full
  recipe-build capability is an explicit named exception per the Dream's own
  clause.
- **The image must not assume it is the only instance.** POSIX `flock` on the
  keys inventory is not effective over NFS (`keys.py:707-709`); a shared-volume
  (Mode I) deployment requires one-writer-per-inventory or a lock upgrade.
  Nothing in this Spec's v1 may bake in a sole-instance assumption.
- **Sequencing:** `provision --module` ([[bmad-module-provisioning]]) lands
  ahead of or alongside this work — TTY-only installers cannot run in a `RUN`
  layer either. Whichever effort adds Steward's fifth duty module first executes
  the deferred shared `render_error(ns, message)` action item (retro A2.1).
  Image-publish is git/registry sequencing (A2.3's risk class) and gets an
  explicit ordering/partial-failure review pass. Marshal's research sequences
  the container after its § 7 consolidation decision — baking seven
  subprocess-guard variants into an image freezes them.
- `deploy dashboard`'s push step stays host-side (or takes a mounted token) in
  v1 — a named exception, not a blocker (A3.5).

## Non-goals

- **The packaging-full tier.** No `local-recipes`/CFE/rattler-build image here;
  if a two-tier split happens it is decided under the open question above, with
  Marshal's unification research as the reference — not duplicated into this
  contract.
- **Mode I (with-infrastructure) design.** Registry publication, ARC-style
  per-runner containers, budget enforcement at the container boundary: named as
  the future that must not be foreclosed, designed elsewhere.
- **Rearchitecting station code.** The walk-up anchoring, AD-1 wrapping, and
  env-var routing are consumed as-is; this Spec packages them, it does not
  change them.

## Success signal

One `podman build` yields one image; a rootless `podman run` boots `marshal` and
reaches all eight station CLIs; the secret gate over the rootfs finds nothing;
the same image runs behind Artifactory by env vars alone; state volumes survive
container replacement.

## Nothing builds the image — 2026-09-09

**The signal above has never been exercised in CI**, and the two surviving Mode questions are not
decidable until it is. No workflow and no pixi task builds the root `Containerfile`; the
`container-gates` and `container-volumes` pixi tasks (`pixi.toml:556`, `:569`) are invoked by
nothing. CAP-5 — "the image proves itself at build time" — has no build time to prove itself at.

**Vessel: new steward Story 48.10** (batch § 2.3 C7 / rows stB-B5 / stB-B7) — a job or pixi task
invoked by `pyforge-station-tests.yml` that builds the root `Containerfile` and runs
`container-gates secrets-scan` + `container-volumes` on the result, landed **before Story 44.10
closes the CI window**. The Spec stays `shipped` — Epic 7 delivered every capability it names —
but the container half of the fleet's realization gate is unexercised until 48.10 lands.
