---
sources:
  - src/platform/config/urls.py
  - src/platform/compose/compose.yml
  - src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - pixi.toml
verified: 2026-09-20
---

# PyForge Ecosystem Architecture

This document provides a conceptual overview of the PyForge ecosystem, aiming to help New Developers and Platform Builders understand the relationship between the central platform and the isolated stations.

## The Canopy Host (`src/platform/`)
At the center of the PyForge ecosystem is the **Canopy** — a monolithic host built on Django and Wagtail CMS.
The Canopy acts as the central interface, persistence layer, and API provider for the enterprise.

- **State Management:** It houses the PostgreSQL database models, user sessions, and Wagtail configuration.
- **Agent Interfacing:** It provides endpoints that the various AI engines (e.g., DB-GPT, Langflow, Python Agent Platform) can consume.
- **Isolation Rule:** The `src/platform/` layer **never** imports `pyforge.*` module code directly. It maintains strict architectural boundaries.

## The Eight Stations (`src/shared/packages/pyforge-*/`)
Orbiting the Canopy are eight isolated Python packages known as **Stations**. These are independent factory modules designed to be operated either by humans or by autonomous BMAD agents.

The 8 stations are:
1. **Atlas**: Kedro/DuckDB data pipelines over the conda-forge and PyPI universes (the cf_atlas intelligence layer and its dashboard).
2. **Doctor**: System diagnostics and the detector sources behind `detectors-ci`; findings stay advisory, never a second PR gate.
3. **Herald**: The Dream-to-deck bridge (Claude Design decks) plus progress, success-claim and operational-notice moments.
4. **Marshal**: The BMAD-loop dispatch/loop supervisor — launches, watches, lands and retires story sessions (`marshal factory dispatch`, `marshal factory drain`, `marshal watch`, `marshal land`, `marshal retire`, `marshal refresh`).
5. **Mason**: Build engineering — conda recipe authoring and builds (wrapping `conda-forge-expert`), package shipping, environment resolution.
6. **Scribe**: Team memory, fact ledgers, and context retrieval (`scribe capture` / `scribe recall`).
7. **Steward**: Workspace provisioning, credential lifecycle (`steward keys`), platform deployment, and environment lifecycle.
8. **Warden**: Security, CVE scanning, and policy enforcement (`warden scan`, the one PR gate).

### The Unified CLI Adapter
Because the Canopy host cannot import station code, and stations must remain isolated from one another, all interactions occur via a unified CLI adapter.

When you run a command like:
```bash
pixi run -e pyforge-guild pyforge steward workspace start my-project
```
You are executing a CLI entry point defined within `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`. The `pyforge` executable (`src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py`) acts as a router, mapping the station token to that distribution's own console script (`steward`, `marshal`, `scribe`, `doctor`, …) and forwarding the remaining arguments. `pyforge-guild` is the session default environment; it carries the `doctor`, `marshal`, `scribe` and `steward` console scripts (so `pyforge --help` there lists exactly those four stations). `herald`, `mason`, `warden` and `pyforge-atlas` are installed only in their own `pyforge-<station>` environments, which also own each station's test/build tasks.

## AI Engines
The PyForge Estate supports direct integration with AI orchestration engines. Langflow mounts inside the platform image as a pluggable Django app; DB-GPT runs as a sidecar container beside the Canopy (`src/platform/compose/compose.yml`). Either can invoke the PyForge Station CLIs or interact with the platform's API to perform automated tasks.

For a deeper look into the planning methodology that drives these agents, see [The Tier Model and Data Flow](the-tier-model-and-data-flow.md).
