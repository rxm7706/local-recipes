---
spec: unified-container
status: draft
owner-dream: docs/dreams/unified-container.md
surface:
  - Containerfile                     # multi-stage: pixi-install lean env -> checkout at /pyforge -> entrypoint marshal
  - pixi.toml                         # new composed `pyforge-container` env (pyforge-ci precedent)
  - scripts/container-gates           # image gates: keys audit --secrets over rootfs; provision --verify + per-station --help smoke
sources:
  - ../../../../../../docs/dreams/unified-container.md
  - ../../research/technical-steward-pixi-workspace-member-research-2026-07-25.md   # Addendum A3/A4 — the feasibility study this Spec formalizes
  - ../../../pyforge-marshal/planning-artifacts/research/technical-pyforge-unification-2026-08-08.md   # § 2 — the orchestration half
open_questions:
  - "One image or two: the lean all-stations image (Mode L) vs a
    `pyforge-factory-full` packaging tier with local-recipes/CFE — Marshal's
    research recommends two tiers; this Spec commits only to the lean one and
    leaves the split undecided."
  - "Baked checkout vs bind-mount as the primary mode (A3.6 recommends baked,
    with bind-mount over /pyforge as the dev override) — decide at epic time."
  - "Worktree placement for in-container bmad-loop runners (container fs vs
    volume) — deferred with Mode I; Mode L runs loops against a mounted host
    checkout exactly as today."
  - "Whether Mode L and the with-infrastructure Mode I are the same image with
    different mounts/limits, or Mode I forks — nothing here may foreclose
    Mode I, but its design is out of scope."
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
