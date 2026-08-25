---
title: One pixi env for the platform image
type: dream
owner: steward
status: specified
---

# One pixi env for the platform image

## The Dream

The platform image is one locked environment. A `pixi install --frozen -e python-agent-platform`
already contains Langflow, DB-GPT, and the Django-host extras that today arrive as a second
`pip install --no-deps` layer. Overlaps with conda fail at **lock** time, not as a build-time
uninstall that silently replaces `mcp`.

## What it looks like when real

- `src/platform/Containerfile` has no `python3 -m pip install --no-deps` RUN.
- `[feature.platform-image-pip]` is gone (or is not an installer); pins live on the env the
  image actually materializes.
- Rebuilding the image after a lock change does not uninstall conda `mcp` / `sse-starlette` /
  `python-multipart`.
- Pixitainer is **re-evaluated** as a Docker/Podman backend against the Story 10.3 contract
  (UBI9-minimal, no pixi in the runtime, GID 0, gunicorn CMD). If it still fails, the
  hand-rolled Containerfile stays and only the pip RUN dies.

## What is real

Story 16.1 made `[feature.platform-image-pip]` the sole *authority* for that pip layer; the
Containerfile still *installs* it with pip. CRC 2026-08-25 showed pip `--no-deps` uninstalling
conda `mcp` 1.28.1. Steward 12-7 is **done** (`/ht/` 200); this Dream is the queued follow-up
in `.cursor/pyforge-fleet-drain/NEXT-AFTER-12-7.md`.

Story 10.3 already rejected conda-forge `pixitainer` 0.8.3 (`pixi-containerize` → Apptainer
SIF). Mason presenton still uses pixitainer for other images. This Dream re-evals
`pixitainer-docker` only; it does not reopen a shared pixi *base* image
(`docs/dreams/pixi-container-image.md`).

## Constraints

- `platform-ci-test` stays a separate PyPI solve (psycopg3 vs image psycopg2).
- Runtime stage still copies the materialized env — **no pixi binary** in the final image.
- `python-agent-platform` may keep `mcp <2` for Langflow/FastMCP; host MCP 2.0 faces are not
  solved by folding the pip layer alone.
- Do not mix `meta.yaml` / `recipe.yaml`. Invoke `conda-forge-expert` if this effort touches
  recipes.

## Non-goals

- Re-proving steward 12-7 (Route / SCC / PVC / UID).
- Merging `platform-ci-test` into `python-agent-platform`.
- A repo-owned pixi base image (`pixi-container-image`).
- Eight stations in one image (`unified-container`).

## Realization log

- **2026-08-25** — Dream captured after 12-7 close. Intent from `NEXT-AFTER-12-7.md`. Spec:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-platform-image-one-pixi-env/`.
