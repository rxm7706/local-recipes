---
sources:
  - pixi.toml
  - src/platform/Containerfile
  - src/platform/compose/compose.yml
  - src/platform/compose/dbgpt/Containerfile
  - docs/explanation/platform-deployment-architecture.md
verified: 2026-09-20
---

# AI Engine Operations

The PyForge Estate supports multiple agentic engines integrated directly with the platform. Langflow and the Django host share the `python-agent-platform` environment defined in `pixi.toml` (the image's env); DB-GPT has its own `dbgpt-sidecar` environment because its `fastapi` pin is disjoint from Langflow's.

## Spinning up the Local Environment

To run the full stack locally without Docker (PostgreSQL + pgvector, Redis, and the Silo S3-compatible object store all ship as per-user server processes), use the `platform-dev` environment, which composes `python-agent-platform` with those local services.

1. **Install the environment:**
   ```bash
   pixi install -e platform-dev
   ```

2. **Run the services:**
   Start the per-user PostgreSQL, Redis and Silo processes from that env (`pixi shell -e platform-dev`, then `pg_ctl` / `redis-server` / `silo`), or bring up the container stack instead with `docker compose -f src/platform/compose/compose.yml up` (postgres, redis, the platform image, and the `dbgpt` sidecar). The Django-side steps are in [Local Platform Development](../tutorials/local-platform-development.md).

## Running the DB-GPT Sidecar

DB-GPT operates as a sidecar container in production (`src/platform/compose/dbgpt/Containerfile`), but locally it can be tested using its dedicated environment.

1. **Enter the environment:**
   ```bash
   pixi shell -e dbgpt-sidecar
   ```

2. **Start the server:**
   Use the standard DB-GPT webserver CLI to launch the FastAPI router:
   ```bash
   dbgpt start webserver
   ```

## Building the Python Agent Platform image

The core image mounts Langflow and the Django host into a single interpreter (`python 3.14.*`). Its multi-stage `src/platform/Containerfile` materializes the `python-agent-platform` env straight from `pixi.lock` (`pixi install --frozen -e python-agent-platform`) — there is no `environment.yaml` export step, and the repo-root `environment.yaml` belongs to the `build` env, not to this image.

Build it from the repository root (the build context must be the root, because `pixi.toml` / `pixi.lock` live there):
```bash
docker build -f src/platform/Containerfile -t platform-test .
```

For more details on how these engines interact with the Canopy monolithic architecture, see the [PyForge Estate Overview](../explanation/pyforge-estate-overview.md).
