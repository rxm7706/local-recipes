---
spec: platform-image-one-pixi-env
status: shipped
created: "2026-08-25"
updated: "2026-08-25"
owner-dream: docs/dreams/platform-image-one-pixi-env.md
surface:
  - src/platform/Containerfile
  - pixi.toml
  - pixi.lock
  - scripts/platform_image_pip_layer.py
  - [feature.python-agent-platform]
  - "[feature.python-agent-platform.dependencies] (host extras; retired pypi table)"
companions:
  - pixitainer-eval.md
sources:
  - ../../../../../../docs/dreams/platform-image-one-pixi-env.md
  - ../../../../../../.cursor/pyforge-fleet-drain/NEXT-AFTER-12-7.md
  - spec-10-3-one-image-both-engines.md
open_questions: []
---

> **Canonical contract.** This SPEC and `companions:` are what to build. Steward 12-7 is
> **done**; do not re-prove CRC Route/SCC here. Do not code from the queue note alone.

# SPEC — One pixi env for the platform image

## Why

**A pain to solve.** The Story 10.3 / 16.1 image still materializes `python-agent-platform`
from conda, then `pip install --no-deps` from `[feature.platform-image-pip]`. On CRC
(2026-08-25) that second installer **uninstalled** conda `mcp` 1.28.1 (and
`sse-starlette` / `python-multipart`). Overlaps must fail at **lock**, not at image build.
A full `podman build` also hit conda **503**; a single frozen env is the lock the rebuild
can retry without a pip seam.

## Capabilities

- **CAP-1 — one frozen env**
  - **intent:** The platform image is produced from a single `pixi install --frozen -e
    python-agent-platform` whose lock already contains the Django-host extras that today
    live in `[feature.platform-image-pip]`.
  - **success:** After `pixi lock`, a planted overlap (e.g. pip `mcp` vs conda `mcp`) is a
    **solve failure**, not a Containerfile uninstall. The image interpreter imports
    `django_structlog` (and the other extras that are not conda-provided) without a pip
    layer RUN.
  - **verified:** 2026-09-11 — live: `pixi run -e python-agent-platform python -c "import
    django_structlog"` succeeds with no pip layer; `[feature.platform-image-pip]` is gone
    from `pixi.toml` entirely (not merely retired); `tests/packaging/test_platform_image_
    one_pixi_env.py` 3/3 pass. The planted-overlap → solve-failure claim itself (deliberately
    breaking the lock to watch it fail) not re-exercised — would require mutating pixi.toml
    and a full re-lock, disproportionate to a doc-hygiene sweep.

- **CAP-2 — Containerfile drops the pip installer**
  - **intent:** The runtime image no longer runs `python3 -m pip install --no-deps` for
    host extras. `[feature.platform-image-pip]` and `scripts/platform_image_pip_layer.py`
    are retired or reduced to a tombstone that fails if resurrected.
  - **success:** `rg 'pip install --no-deps' src/platform/Containerfile` is empty; the
    16.1 emitter is unused by the Containerfile; platform-ci-test still exists as its own
    env.
  - **verified:** 2026-09-11 — live: `rg 'pip install --no-deps' src/platform/Containerfile`
    returns no match; `platform_image_pip_layer.py`'s own docstring reads "Retired... must
    not come back as an installer"; `platform-ci-test` env still present at `pixi.toml:878`.

- **CAP-3 — pixitainer-docker re-eval**
  - **intent:** Re-test the **Docker/Podman** pixitainer backend against the Story 10.3
    contract recorded in `pixitainer-eval.md`. If any must-hold row fails, keep the
    hand-rolled Containerfile and only apply CAP-1/CAP-2.
  - **success:** A dated Design Note lists each table row pass/fail with the CLI/package
    actually invoked. A fail does not reopen SIF-only `pixi-containerize`. Mason presenton
    pixitainer usage is untouched.
  - **verified:** 2026-09-11 — `pixitainer-eval.md` carries a dated "Design Note — 2026-08-25
    (`pixitainer-docker` 0.8.3)" section with per-row pass/fail and the CLI/package cited
    (`docker-cli`, `ENTRYPOINT pixi run --locked`); the recorded outcome is Fail, and the hand-
    rolled Containerfile was kept — consistent with the success clause.

## Constraints

- Runtime stage copies the materialized env; **no pixi binary** in the final image (10.3).
- UBI9-minimal, GID 0 `g+rwX` on the three writable paths, `restricted-v2` (10.3).
- `platform-ci-test` remains a separate conda solve (psycopg3 vs image psycopg2).
- Folding extras does **not** lift `python-agent-platform` to `mcp` 2.0 while FastMCP 3.x
  on that env declares `mcp >=1.24,<2`. Host MCP faces on CRC may stay ImportError-skipped
  until a later mcp/FastMCP story.
- Recipe authoring requires `conda-forge-expert`. No mixed `meta.yaml`/`recipe.yaml` runs.
- Never `scripts/bmad-switch` from a parallel agent; write this spec under
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` literally.

## Non-goals

- Steward 12-7 live-cluster proofs.
- Merging `platform-ci-test` into `python-agent-platform`.
- A repo-owned pixi base image (`spec-pixi-container-image`).
- Eight stations in one image (`unified-container`).
- Inventing a `mcp` 2.0 + Langflow coexistence in this chain.

## Success signal

`pixi install --frozen -e python-agent-platform` then `podman build -f src/platform/Containerfile`
produces an image with **no pip `--no-deps` layer**, host extras importable, and no conda
package uninstalled by pip. Pixitainer either meets `pixitainer-eval.md` or is explicitly
rejected again with the same 10.3 reasons plus any new Docker-backend evidence.

## Assumptions

- Django-host extras ship from conda-forge on `[feature.python-agent-platform.dependencies]`
  (whitenoise `>=6.11`; cookiecutter `6.9.0` is not on conda-forge). `platform-ci-test`
  stays a separate conda solve.
- Conda 503 during image build is an infra flake; CAP-1 does not require a second installer
  as a workaround.

## Open Questions

- ~~**extras-on-python-agent-platform-vs-composed-env**~~ — **answered 2026-08-25: extras
  on the feature.** Pins live in `[feature.python-agent-platform.dependencies]` (conda-forge)
  so `platform-dev` inherits them. Not a composed extra feature. `mcp-types` / `httpx2` were
  **not** folded (would pull mcp 2.x; FastMCP 3.x still `mcp<2`).
