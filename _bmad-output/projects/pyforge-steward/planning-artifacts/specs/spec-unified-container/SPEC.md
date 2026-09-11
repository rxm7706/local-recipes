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
updated: "2026-09-11"
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
  - "RESOLVED 2026-09-11 (was BLOCKER, 2026-09-09): Story 48.10 landed 2026-09-10 and wired
    `.github/workflows/pyforge-station-tests.yml`'s `guild-container` job to build the root
    `Containerfile` on a docker/podman matrix (`scripts/guild_image_ci.sh`), running
    `container-gates secrets-scan` + `volumes-roundtrip` post-build — re-verified live locally
    2026-09-11 on both engines. The image-build blocker is gone; the two Mode questions above are
    now decidable on their own design merits (still genuinely open, unrelated to this resolution)."
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
  - **verified:** 2026-09-11 — live, full end-to-end: `podman build -f Containerfile`
    (this pass, local — rootless confirmed via `podman info .Host.Security.Rootless=true`)
    completed clean from the unmodified root `Containerfile`, producing a 3.5 GB image (the
    lean `pyforge-container` env, not `local-recipes`'s ~9.8 GB). Then `podman run --rm
    --entrypoint /entrypoint.sh <image> <cli> --help` was run directly (not just the
    build-time gate) for all eight real console scripts — `marshal`, `steward`,
    `pyforge-atlas`, `warden`, `doctor`, `mason`, `herald`, `scribe` — all OK. No compose
    file used; no podman daemon/service started (`ServiceIsRemote=false`, podman's normal
    fork-exec rootless mode). `docker build` of the same Containerfile also verified clean in
    the same pass (4.72 GB image) — both matrix legs green, matching CI's
    `guild-container` job (`.github/workflows/pyforge-station-tests.yml`).
- **CAP-2 — the image ships the repo at a fixed short path.** Intent: all four
  duty modules (`keys.py`, `provision.py`, `deploy.py`, `budget.py`) locate the
  repo by marker-file walk-ups, and `keys.py` imports CFE's `_http.py` from the
  checkout at import time — so the image ships the checkout at `/pyforge`, not
  wheels into a bare filesystem. Success: every marker walk-up resolves
  in-container unchanged; `/pyforge` also trivially satisfies the >~173-byte
  worktree path-length limit that panics pixi-build-python.
  - **verified:** 2026-09-11 — code-level: `keys.py` walks up from its own resolved location
    for the marker file (docstring confirms) and imports `_http.auth_headers_for` at module
    top level (`keys.py:104`, import-time, not lazy) — matches the claim exactly.
- **CAP-3 — credentials never enter image layers.** Intent: `age` identity files
  arrive as Podman secrets (tmpfs-mounted at run time); `_http.py` routing stays
  env-var-only (`podman run -e`/`--env-file`), so the air-gapped container is the
  same container with different env vars. Success: `steward keys audit --secrets`
  runs over the unpacked image rootfs as a build gate (the shipped scanner needs
  zero changes) and finds nothing; no identity, token, or enterprise URL in any
  layer.
  - **verified:** 2026-09-11 — code-level: `scripts/container-gates`'s `secrets-scan`
    delegates entirely to `steward keys audit --secrets` (no second scanner, matches AD-2),
    wired as a Containerfile `RUN` step in the final stage. The one documented, permanent,
    unavoidable finding (`age-keygen`'s compiled-in upstream test-vector string) is named and
    excluded by design, not silently swept.
- **CAP-4 — state outlives the container.** Intent: mutable state mounts as
  volumes — `.steward/` (keys inventory, budget ceilings), the gitignored
  `.claude/data/conda-forge-expert/` runtime state, loop homes — so rotation and
  ceiling history survive container replacement. Success: replace the container,
  `steward keys list` / `budget check` answer from the surviving volume.
  - **verified:** 2026-09-11 — code-level: `container-gates volumes-roundtrip --image IMAGE
    --mount PATH` is real, implemented code (writes to a mounted path, replaces the container,
    reads it back, fails loudly on mismatch/timeout) — not aspirational text.
- **CAP-5 — the image proves itself at build time.** Intent: image smoke gates
  run `steward provision --verify` plus each station CLI's `--help` before an
  image is accepted. Success: a broken station wiring fails the build, not the
  first operator.
  - **verified:** 2026-09-11 — live: the two build runs above (docker + podman) both executed
    the Containerfile's two build-time `RUN` gates in-line — `container-gates secrets-scan`
    (clean) and `container-gates cli-smoke --cli 'marshal --help' ... ` for all eight stations
    (all OK) — and would have failed the `docker build`/`podman build` itself (and did, per
    Story 48.10's own CI job `guild-container` in `pyforge-station-tests.yml`, which builds
    the root Containerfile and is the first workflow ever to do so) had any station been
    broken. **One precise textual mismatch found:** the shipped gate is
    `container-gates cli-smoke` (per-station `--help`), not a literal `steward provision
    --verify` call — grepping the Containerfile finds no `provision --verify` RUN step, and
    `provision --verify` in `steward/provision.py` is actually the *repo* `environment.yaml`-
    vs-`pixi.toml` PR-CI sync check (an unrelated command), not an image-wiring check. The
    stated SUCCESS criterion ("a broken station wiring fails the build, not the first
    operator") is fully met by `cli-smoke`; the specific tool name in the intent text is
    stale/inaccurate and should be corrected to `container-gates cli-smoke`.

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

## RESOLVED 2026-09-11 — the image now builds in CI (was: "Nothing builds the image")

**Story 48.10 landed 2026-09-10** (`sprint-status-ledger.yaml`:
`48-10-the-one-container-guild-proves-itself-at-build-time-ci-builds-the-root-containerfile: done`;
commit `fbea18043c`). `.github/workflows/pyforge-station-tests.yml`'s `guild-container` job now
builds the root `Containerfile` on a docker/podman matrix via
`pixi run --frozen -e pyforge-steward pyforge-steward-guild-image-build` (`scripts/guild_image_ci.sh`),
running `container-gates secrets-scan` + `container-gates volumes-roundtrip` post-build, on top of
the Containerfile's own in-line `secrets-scan` + `cli-smoke` build-time `RUN` gates. Re-verified
locally 2026-09-11 (both engines, see CAP-1/CAP-5 `verified:` entries above) — the signal in
"Success signal" above is real and exercised, not merely aspirational. The two surviving Mode
questions in `open_questions` above remain genuinely open (unrelated to this resolution — they are
design-scope questions, not "does the image build" questions).
