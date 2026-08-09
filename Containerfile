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

ENTRYPOINT ["/entrypoint.sh"]
CMD ["marshal"]
