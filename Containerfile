# Story 7.1 ("One build, whole Guild"): multi-stage build following pixi's
# own documented container-deployment pattern -- a pixi builder stage
# materializes the lean `pyforge-container` env (pixi.toml's composition of
# the eight pyforge-* station features), and a minimal ubuntu runtime stage
# copies the full checkout + materialized env + shell-hook script, with no
# pixi binary in the final image. `marshal` is the default in-container
# front door; every other station CLI stays reachable by overriding CMD
# (e.g. `docker run <image> steward --version`; console-script names vary
# per station -- atlas's is `pyforge-atlas`, not `atlas` -- see each
# package's [project.scripts] in pyproject.toml).
#
# BUILD: `docker build -f Containerfile -t pyforge-guild .` from the repo
# root. The `-f` is not optional under docker/BuildKit, which only
# auto-detects the name `Dockerfile`; podman and buildah also accept
# `Containerfile` unflagged. The name is deliberate -- this is an OCI image
# definition, not a docker-specific one.
#
# SCOPE OF THIS IMAGE (Story 7.1): it materializes the eight station CLIs and
# nothing else. The runtime stage carries no `git`, `gh`, `pixi` or `tmux`
# binary, so station code paths that subprocess-wrap them (marshal's git
# worktree orchestration, steward's `provision`/`deploy build`) cannot run
# in-container yet; `herald deck` is likewise host-only because
# `.dockerignore` strips `presentations/` -- and note that half of it is
# host-only QUIETLY: `herald deck seed` raises a HeraldError, but `herald
# deck status` returns `[]` at rc 0, because `_known_slugs()` guards its
# scan with `if presentations_dir.is_dir()`. In-container that inverts the
# guarantee its own docstring states ("reported as unlinked rather than
# silently omitted"). Do not read `[]` from this image as "the Guild has no
# decks"; the host had 14 at the time of writing. Fixing herald's own code
# is out of this story's scope (station code is consumed as-is) and is
# logged to deferred-work.md. That is a consequence of this
# story's Always constraint -- compose the eight existing pyforge-* features
# verbatim, no new dependency curation -- and is logged to deferred-work.md,
# not an oversight. What IS contracted here: the build succeeds, all eight
# CLIs answer `--version`, and bare `docker run` lands on `marshal`.
#
# EVERY INVOCATION MUST GO THROUGH THE ENTRYPOINT. The station CLIs are on
# PATH only because /entrypoint.sh sources the shell-hook, and that hook also
# exports CONDA_PREFIX and runs this env's three package activation scripts
# (libarrow, libglib, libxml2-split), which contribute GSETTINGS_SCHEMA_DIR
# and XML_CATALOG_FILES. (Verified in the built image, because an earlier
# revision of this comment named SSL_CERT_FILE / GDK_PIXBUF_MODULE_FILE /
# FONTCONFIG_FILE here and all three are in fact EMPTY -- no activate.d
# script in this env sets them. The decision below is unchanged; only its
# evidence was wrong.) Paths that bypass the entrypoint -- `docker exec <ctr>
# marshal`, `docker run --entrypoint marshal <image>` -- fail with
# "executable file not found". Deliberately NOT papered over with a baked
# `ENV PATH`: that would make those paths resolve the binary while still
# missing the activation env, trading a loud failure for a quiet one. Use
# `docker exec <ctr> /entrypoint.sh marshal ...` instead.
#
# --platform=linux/amd64 pinned on both stages: the workspace's pixi.toml
# declares linux-64/win-64/osx-arm64-min only (no linux-aarch64), so building
# on an arm64 Docker host (e.g. Apple Silicon) without this pin makes `pixi
# install --frozen` fail outright -- no matching lock entry for the host's
# native arch.

FROM --platform=linux/amd64 ghcr.io/prefix-dev/pixi:0.76.1 AS builder

# WORKDIR /pyforge -- fixed, short, and literal by design, not merely the
# default choice. `/pyforge` is deliberately NOT a build ARG or ENV: this
# repo's own worktree tooling has a documented path-length panic in
# `pixi-build-backends` -- crates/pixi-build-backend/src/tools.rs::
# output_directory does an unchecked `usize` subtraction that underflows
# once <workspace-root> plus a per-package build-dir suffix exceeds 255
# bytes, which empirically panics around a ~173-byte workspace root for
# this repo's package-name lengths (auto-memory
# project_bmad_loop_worktree_path_length_limit). A build ARG/ENV here would
# reopen exactly that "can grow past the ceiling" risk; a hardcoded literal
# forecloses it. `/pyforge` is 8 bytes -- roughly 20x margin under the
# ~173-byte ceiling. Every duty module locates the repo root by
# marker-file walk-up (see the "Full repo checkout" comment on the runtime
# stage below), which is mount-point agnostic -- nothing hardcodes a host
# path -- so any short fixed root would work; `/pyforge` is simply the one
# this repo settled on. Full analysis:
# _bmad-output/projects/pyforge-steward/planning-artifacts/research/technical-steward-pixi-workspace-member-research-2026-07-25.md
# § A3.1.
WORKDIR /pyforge
COPY . /pyforge

# --frozen: install EXACTLY what pixi.lock says and never re-solve inside the
# build, so the image is a function of the committed lock alone. Note what it
# does NOT do: per `pixi install --help`, `--frozen` "doesn't update lock file
# if it isn't up-to-date with the manifest" -- it is silent about staleness,
# not loud. `--locked` is the flag that aborts on a lock/manifest mismatch,
# and it is deliberately not used here: `--frozen` is this repo's convention
# at every call site. Keeping pixi.lock in step with pixi.toml therefore
# remains the author's job (`pixi install -e pyforge-container` outside the
# container, or `pixi lock --check` as the probe) -- a stale lock yields a
# green build of an out-of-date image.
RUN pixi install --frozen -e pyforge-container

# The activation script for `pyforge-container` -- sourced by the runtime
# entrypoint below so every station CLI lands on PATH without shipping the
# pixi binary itself into the runtime stage.
RUN pixi shell-hook -e pyforge-container -s bash > /shell-hook.sh

FROM --platform=linux/amd64 ubuntu:24.04

# WORKDIR /pyforge -- same fixed short root as the builder stage; see the
# rationale comment there.
WORKDIR /pyforge

# Full repo checkout, not just the installed packages: every station duty
# module locates the repo root by marker-file walk-up, and
# `steward/keys.py` imports CFE's `_http.py` from the checkout at import
# time -- so the image needs the whole tree, not a curated subset.
COPY --from=builder /pyforge /pyforge
COPY --from=builder /shell-hook.sh /shell-hook.sh

# `exec -- "$@"`, not `exec "$@"`: without the `--` terminator bash parses a
# leading-dash first argument as its OWN option. Two live consequences, both
# reachable by typing something reasonable at a `CMD ["marshal"]` image:
# `docker run <image> --version` died with "exec: --: invalid option" (rc 2,
# a message about bash, not about the image), and `docker run <image> -c
# /usr/bin/env` silently ran the command in a sub-shell with an EMPTY
# environment, rc 0 -- precisely the quiet failure the header above refuses
# to trade a loud one for.
RUN printf '#!/bin/bash\nset -e\nsource /shell-hook.sh\nexec -- "$@"\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

# Story 7.3 ("Credentials never enter image layers") build-time gate:
# `scripts/container-gates secrets-scan` delegates to the existing `steward
# keys audit --secrets <path>` primitive (AD-2 -- no second scanner) over
# every root the image ships (`/pyforge`, `/shell-hook.sh`, `/entrypoint.sh`)
# and fails this `RUN` on any finding, which natively aborts `docker
# build`/`podman build` itself -- not a later `docker run`. A plain `RUN`
# step, not a separate CI script, so it always runs on THIS stage's actual
# content and can never drift out of sync with what the image produces.
# `bash -c "..."`, not a bare `RUN source ...`: `source` is a bash builtin,
# and BuildKit's default `RUN` shell is `/bin/sh` (dash on this base image),
# which doesn't have it -- `/bin/sh: source: not found`, confirmed live.
# Sourcing /shell-hook.sh first puts `steward` (and python3) on PATH the same
# way /entrypoint.sh does at runtime -- the builder stage's `pixi install
# --frozen -e pyforge-container` materialized both under
# /pyforge/.pixi/envs/pyforge-container/, which the COPY above brought along.
#
# `/pyforge` is a DIRECTORY root, so `container-gates` skips its `.pixi/`
# child entirely rather than recursing into it: `.pixi/` is this very
# materialized env, and it ships the `age`/`age-keygen` binaries the `keys`
# duty needs to function at all -- `age-keygen` itself has a literal
# `AGE-SECRET-KEY-1...` string compiled in (an upstream test vector,
# confirmed live: `pixi run -e pyforge-steward steward keys audit --secrets
# .pixi/envs/pyforge-steward/bin` finds exactly that one hit, and `strings
# .../age-keygen | grep AGE-SECRET-KEY-1` shows the literal baked into the
# binary -- not written by this repo or this image). That finding is
# unavoidable and permanent for any image shipping `age`/`age-keygen`, so
# excluding `.pixi/` is the only way this gate is ever green on a clean
# build. `/shell-hook.sh` and `/entrypoint.sh` are FILE roots, scanned
# directly (no `.pixi/`-exclusion logic applies to a file).
RUN bash -c "source /shell-hook.sh \
    && python3 /pyforge/scripts/container-gates secrets-scan /pyforge /shell-hook.sh /entrypoint.sh"

# Story 7.4 ("State outlives the container") mount contract: the three
# durable-state roots PRD FR-25 ("loop homes, the Tier-3 store and mutable
# runtime caches resolve to mounted volumes") and SPEC.md's CAP-4 name (the
# story's own Design Notes resolve FR-25's prose 1:1 onto CAP-4's concrete
# list), so a volume/bind mount attached at these exact paths is what makes
# a container replacement (not just a process restart inside one
# long-lived container) preserve state, proven post-build by
# `scripts/container-gates volumes-roundtrip` (a build-time `RUN` gate
# cannot prove this -- see that script's own header for why).
#   /pyforge/.steward                       -- steward's own durable store:
#     keys inventory + budget ceilings (architecture-spine-documented as
#     "repo-root, tracked... survives bmad-switch" -- that description is of
#     the HOST checkout; `.dockerignore` excludes `.steward/` from the build
#     context like every other secret-shaped path, so no tracked content
#     from the host ever ships in a layer -- every fresh volume here starts
#     empty and is populated only by what a running container writes into
#     it); `steward keys list`/`budget check` answering correctly from this
#     path after a restart is CAP-4's own success measure.
#   /pyforge/.claude/data/conda-forge-expert -- conda-forge-expert's mutable
#     runtime cache (cf_atlas.db, vdb/, cve/, mapping caches) -- gitignored,
#     rebuilt over time, but expensive to lose on every container replace.
#   /root/.bmad-loops                       -- loop homes. `HOME=/root` in
#     this image: confirmed live -- no `USER` directive is set anywhere in
#     this Containerfile, so the runtime stage runs as root by ubuntu:24.04's
#     own default. NOTE: this declares the MOUNT POINT only. Story 7.1's
#     SCOPE comment above already documents that `git`/`gh`/`pixi`/`tmux`
#     are absent from this runtime stage, so `steward provision --runner
#     bmad-loop` cannot actually materialize a worktree here -- that gap is
#     unchanged by this story and stays logged to deferred-work.md. This
#     story proves the mount point preserves whatever bytes land there, not
#     that loop orchestration runs in-container.
# FOR FUTURE EDITORS: this must stay the LAST content-writing instruction in
# this stage. Any later `RUN` that writes into one of these three paths
# would write into an anonymous volume for that RUN's own layer, not the
# image layer -- the write would silently vanish from the built image (the
# classic Docker `VOLUME` gotcha). Add new `RUN`/`COPY` steps ABOVE this
# line, not below it.
VOLUME ["/pyforge/.steward", "/pyforge/.claude/data/conda-forge-expert", "/root/.bmad-loops"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["marshal"]
