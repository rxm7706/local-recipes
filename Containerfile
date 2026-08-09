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
# --platform=linux/amd64 pinned on both stages: the workspace's pixi.toml
# declares linux-64/win-64/osx-arm64-min only (no linux-aarch64), so building
# on an arm64 Docker host (e.g. Apple Silicon) without this pin makes `pixi
# install --frozen` fail outright -- no matching lock entry for the host's
# native arch.

FROM --platform=linux/amd64 ghcr.io/prefix-dev/pixi:0.76.1 AS builder

WORKDIR /pyforge
COPY . /pyforge

# --frozen: fail loudly on a stale pixi.lock rather than silently re-solving
# inside the build -- the lock file is the source of truth, kept in sync by
# `pixi install -e pyforge-container` outside the container.
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

RUN printf '#!/bin/bash\nset -e\nsource /shell-hook.sh\nexec "$@"\n' > /entrypoint.sh \
    && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["marshal"]
